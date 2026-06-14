#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "hardware/flash.h"
#include "hardware/sync.h"
#include "tusb.h"
#include "keyboard_usb_descriptors.h"

typedef struct {
    uint pin;
    uint8_t default_key;
    const char *name;
} key_pin_t;

// HID key codes: 1-0 and A-K
#define KEY_1 0x1E
#define KEY_2 0x1F
#define KEY_3 0x20
#define KEY_4 0x21
#define KEY_5 0x22
#define KEY_6 0x23
#define KEY_7 0x24
#define KEY_8 0x25
#define KEY_9 0x26
#define KEY_0 0x27
#define KEY_A 0x04
#define KEY_B 0x05
#define KEY_C 0x06
#define KEY_D 0x07
#define KEY_E 0x08
#define KEY_F 0x09
#define KEY_G 0x0A
#define KEY_H 0x0B
#define KEY_I 0x0C
#define KEY_J 0x0D
#define KEY_K 0x0E

#define DEFAULT_P1_TRIGGER_PIN 7
#define DEFAULT_P1_COIN_PIN 17
#define DEFAULT_P2_TRIGGER_PIN 11
#define DEFAULT_P2_COIN_PIN 21
#define DEFAULT_P1_RELAY_PIN 26
#define DEFAULT_P2_RELAY_PIN 27

#define INACTIVE_TIMEOUT_MS 180000u
#define RELAY_TEST_MS 1000u
#define HID_INTERVAL_MS 10u
#define STATUS_INTERVAL_MS 80u
#define LOGIC_INTERVAL_MS 5u

#define FLASH_TARGET_OFFSET (PICO_FLASH_SIZE_BYTES - FLASH_SECTOR_SIZE)
#define CONFIG_MAGIC 0x47544332u // GTC2 - V023 trigger pin selectable

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint8_t relay_active_low;       // 0=ACTIVE HIGH, 1=ACTIVE LOW
    uint8_t p1_coin_active_high;    // 0=DRY/GND active, 1=3.3V pulse active
    uint8_t p2_coin_active_high;
    uint8_t p1_relay_pin;
    uint8_t p2_relay_pin;
    uint8_t p1_coin_pin;
    uint8_t p2_coin_pin;
    uint8_t p1_trigger_pin;
    uint8_t p2_trigger_pin;
    uint8_t keymap[21];
    uint8_t reserved[26];
} config_t;

static const key_pin_t pins[] = {
    {2,  KEY_1, "GP2=1"},
    {3,  KEY_2, "GP3=2"},
    {4,  KEY_3, "GP4=3"},
    {5,  KEY_4, "GP5=4"},
    {6,  KEY_5, "GP6=5"},
    {7,  KEY_6, "GP7=6/P1_TRIGGER"},
    {8,  KEY_7, "GP8=7"},
    {17, KEY_8, "GP17=8/P1_COIN"},
    {18, KEY_9, "GP18=9"},
    {19, KEY_0, "GP19=0"},
    {9,  KEY_A, "GP9=A"},
    {10, KEY_B, "GP10=B"},
    {11, KEY_C, "GP11=C/P2_TRIGGER"},
    {12, KEY_D, "GP12=D"},
    {13, KEY_E, "GP13=E"},
    {14, KEY_F, "GP14=F"},
    {15, KEY_G, "GP15=G"},
    {16, KEY_H, "GP16=H"},
    {21, KEY_I, "GP21=I/P2_COIN"},
    {22, KEY_J, "GP22=J"},
    {28, KEY_K, "GP28=K"},
};
#define PIN_COUNT (sizeof(pins)/sizeof(pins[0]))

static config_t cfg;
static bool p1_game_active = false;
static bool p2_game_active = false;
static uint32_t p1_last_trigger_ms = 0;
static uint32_t p2_last_trigger_ms = 0;
static uint32_t p1_test_until_ms = 0;
static uint32_t p2_test_until_ms = 0;
static bool p1_relay_on = false;
static bool p2_relay_on = false;

static uint32_t ms_now(void) {
    return to_ms_since_boot(get_absolute_time());
}

static int pin_index(uint pin) {
    for (uint i = 0; i < PIN_COUNT; i++) if (pins[i].pin == pin) return (int)i;
    return -1;
}

static void default_config(void) {
    memset(&cfg, 0, sizeof(cfg));
    cfg.magic = CONFIG_MAGIC;
    cfg.relay_active_low = 0;
    cfg.p1_coin_active_high = 0;
    cfg.p2_coin_active_high = 0;
    cfg.p1_relay_pin = DEFAULT_P1_RELAY_PIN;
    cfg.p2_relay_pin = DEFAULT_P2_RELAY_PIN;
    cfg.p1_coin_pin = DEFAULT_P1_COIN_PIN;
    cfg.p2_coin_pin = DEFAULT_P2_COIN_PIN;
    cfg.p1_trigger_pin = DEFAULT_P1_TRIGGER_PIN;
    cfg.p2_trigger_pin = DEFAULT_P2_TRIGGER_PIN;
    for (uint i = 0; i < PIN_COUNT; i++) cfg.keymap[i] = pins[i].default_key;
}

static bool config_valid(const config_t *c) {
    if (c->magic != CONFIG_MAGIC) return false;
    if (c->relay_active_low > 1 || c->p1_coin_active_high > 1 || c->p2_coin_active_high > 1) return false;
    if (c->p1_relay_pin > 28 || c->p2_relay_pin > 28) return false;
    if (c->p1_coin_pin > 28 || c->p2_coin_pin > 28) return false;
    if (c->p1_trigger_pin > 28 || c->p2_trigger_pin > 28) return false;
    return true;
}

static void load_config(void) {
    const config_t *stored = (const config_t *)(XIP_BASE + FLASH_TARGET_OFFSET);
    if (config_valid(stored)) memcpy(&cfg, stored, sizeof(config_t));
    else default_config();
}

static void save_config(void) {
    uint8_t sector[FLASH_SECTOR_SIZE];
    memset(sector, 0xFF, sizeof(sector));
    memcpy(sector, &cfg, sizeof(config_t));
    uint32_t ints = save_and_disable_interrupts();
    flash_range_erase(FLASH_TARGET_OFFSET, FLASH_SECTOR_SIZE);
    flash_range_program(FLASH_TARGET_OFFSET, sector, FLASH_SECTOR_SIZE);
    restore_interrupts(ints);
}

static bool raw_low(uint pin) {
    return gpio_get(pin) == 0;
}

static bool pin_active(uint pin, bool active_high) {
    return active_high ? (gpio_get(pin) != 0) : raw_low(pin);
}

static bool p1_coin_pressed(void) {
    return pin_active(cfg.p1_coin_pin, cfg.p1_coin_active_high != 0);
}

static bool p2_coin_pressed(void) {
    return pin_active(cfg.p2_coin_pin, cfg.p2_coin_active_high != 0);
}

static bool p1_trigger_pressed(void) {
    return raw_low(cfg.p1_trigger_pin);
}

static bool p2_trigger_pressed(void) {
    return raw_low(cfg.p2_trigger_pin);
}

static bool pressed_pin(uint pin) {
    if (pin == cfg.p1_coin_pin) return p1_coin_pressed();
    if (pin == cfg.p2_coin_pin) return p2_coin_pressed();
    return raw_low(pin);
}

static void relay_write(uint pin, bool on) {
    bool level = cfg.relay_active_low ? !on : on;
    gpio_put(pin, level ? 1 : 0);
}

static void set_p1_relay(bool on) {
    p1_relay_on = on;
    relay_write(cfg.p1_relay_pin, on);
}

static void set_p2_relay(bool on) {
    p2_relay_on = on;
    relay_write(cfg.p2_relay_pin, on);
}

static void configure_one_input(uint pin, bool active_high) {
    if (pin == cfg.p1_relay_pin || pin == cfg.p2_relay_pin) return;
    gpio_init(pin);
    gpio_set_dir(pin, GPIO_IN);
    if (active_high) gpio_pull_down(pin);
    else gpio_pull_up(pin);
}

static void configure_inputs(void) {
    for (uint i = 0; i < PIN_COUNT; i++) {
        if (pins[i].pin == cfg.p1_coin_pin) configure_one_input(pins[i].pin, cfg.p1_coin_active_high != 0);
        else if (pins[i].pin == cfg.p2_coin_pin) configure_one_input(pins[i].pin, cfg.p2_coin_active_high != 0);
        else configure_one_input(pins[i].pin, false);
    }
    // Coin / tetik pini tuş listesinde olmasa bile ayrıca input olarak hazırlanır.
    configure_one_input(cfg.p1_coin_pin, cfg.p1_coin_active_high != 0);
    configure_one_input(cfg.p2_coin_pin, cfg.p2_coin_active_high != 0);
    configure_one_input(cfg.p1_trigger_pin, false);
    configure_one_input(cfg.p2_trigger_pin, false);
}

static void configure_relays(void) {
    gpio_init(cfg.p1_relay_pin);
    gpio_init(cfg.p2_relay_pin);
    gpio_set_dir(cfg.p1_relay_pin, GPIO_OUT);
    gpio_set_dir(cfg.p2_relay_pin, GPIO_OUT);
    set_p1_relay(false);
    set_p2_relay(false);
}

static void cdc_write(const char *s) {
    if (!tud_cdc_connected()) return;
    tud_cdc_write_str(s);
    tud_cdc_write_flush();
}

static const char *relay_mode_text(void) { return cfg.relay_active_low ? "LOW" : "HIGH"; }
static const char *p1_coin_text(void) { return cfg.p1_coin_active_high ? "HIGH" : "DRY"; }
static const char *p2_coin_text(void) { return cfg.p2_coin_active_high ? "HIGH" : "DRY"; }

static void send_config(void) {
    char buf[192];
    snprintf(buf, sizeof(buf), "CONFIG,RELAY,%s,P1COIN,%s,P2COIN,%s,RELAYPINS,%u,%u,COINPINS,%u,%u,TRIGGERPINS,%u,%u,TIMEOUT,%u\n",
             relay_mode_text(), p1_coin_text(), p2_coin_text(),
             cfg.p1_relay_pin, cfg.p2_relay_pin, cfg.p1_coin_pin, cfg.p2_coin_pin,
             cfg.p1_trigger_pin, cfg.p2_trigger_pin, INACTIVE_TIMEOUT_MS/1000u);
    cdc_write(buf);
}

static void send_map(void) {
    char buf[384];
    int n = snprintf(buf, sizeof(buf), "MAP");
    for (uint i = 0; i < PIN_COUNT && n < (int)sizeof(buf)-16; i++) {
        n += snprintf(buf+n, sizeof(buf)-n, ",%u:%u", pins[i].pin, cfg.keymap[i]);
    }
    snprintf(buf+n, sizeof(buf)-n, "\n");
    cdc_write(buf);
}

static void send_status(void) {
    if (!tud_cdc_connected()) return;
    char buf[512];
    int n = snprintf(buf, sizeof(buf), "STATUS,KEYBOARD,BTN");
    for (uint i = 0; i < PIN_COUNT && n < (int)sizeof(buf)-80; i++) {
        n += snprintf(buf+n, sizeof(buf)-n, ",%u:%d", pins[i].pin, pressed_pin(pins[i].pin) ? 1 : 0);
    }
    snprintf(buf+n, sizeof(buf)-n, ",RELAYS,%u:%d,%u:%d,ACTIVE,P1:%d,P2:%d,CFG,RELAY:%s,P1COIN:%s,P2COIN:%s,COINPINS:%u:%u,TRIGGERPINS:%u:%u\n",
             cfg.p1_relay_pin, p1_relay_on ? 1 : 0, cfg.p2_relay_pin, p2_relay_on ? 1 : 0,
             p1_game_active ? 1 : 0, p2_game_active ? 1 : 0,
             relay_mode_text(), p1_coin_text(), p2_coin_text(), cfg.p1_coin_pin, cfg.p2_coin_pin,
             cfg.p1_trigger_pin, cfg.p2_trigger_pin);
    cdc_write(buf);
}

static bool is_high_word(const char *s) {
    return strcmp(s, "HIGH") == 0 || strcmp(s, "AH") == 0 || strcmp(s, "1") == 0;
}

static bool is_low_word(const char *s) {
    return strcmp(s, "LOW") == 0 || strcmp(s, "AL") == 0;
}

static void handle_setcfg(char *line) {
    // Formats:
    // SETCFG,HIGH,DRY,HIGH
    // SETCFG,LOW,DRY,DRY,26,27
    // SETCFG,HIGH,DRY,DRY,26,27,3,21,7,11  -> p1 relay, p2 relay, p1 coin, p2 coin, p1 trigger, p2 trigger
    char a[16] = {0}, b[16] = {0}, c[16] = {0};
    unsigned p1rp = cfg.p1_relay_pin, p2rp = cfg.p2_relay_pin;
    unsigned p1cp = cfg.p1_coin_pin,  p2cp = cfg.p2_coin_pin;
    unsigned p1tp = cfg.p1_trigger_pin, p2tp = cfg.p2_trigger_pin;
    int got = sscanf(line + 7, "%15[^,],%15[^,],%15[^,],%u,%u,%u,%u,%u,%u", a, b, c, &p1rp, &p2rp, &p1cp, &p2cp, &p1tp, &p2tp);
    if (got >= 3) {
        if (is_low_word(a)) cfg.relay_active_low = 1; else cfg.relay_active_low = 0;
        cfg.p1_coin_active_high = is_high_word(b) ? 1 : 0;
        cfg.p2_coin_active_high = is_high_word(c) ? 1 : 0;
        if (got >= 5 && p1rp <= 28 && p2rp <= 28 && p1rp != p2rp) {
            cfg.p1_relay_pin = (uint8_t)p1rp;
            cfg.p2_relay_pin = (uint8_t)p2rp;
        }
        if (got >= 7 && p1cp <= 28 && p2cp <= 28) {
            cfg.p1_coin_pin = (uint8_t)p1cp;
            cfg.p2_coin_pin = (uint8_t)p2cp;
        }
        if (got >= 9 && p1tp <= 28 && p2tp <= 28 && p1tp != p2tp) {
            cfg.p1_trigger_pin = (uint8_t)p1tp;
            cfg.p2_trigger_pin = (uint8_t)p2tp;
        }
        configure_inputs();
        configure_relays();
        save_config();
        cdc_write("OK,SETCFG\n");
        send_config();
    } else {
        cdc_write("ERR,SETCFG_FORMAT\n");
    }
}

static void handle_setkey(char *line) {
    // SETKEY,<pin>,<hidcode>
    unsigned pin = 0, key = 0;
    if (sscanf(line + 7, "%u,%u", &pin, &key) == 2) {
        int idx = pin_index(pin);
        if (idx < 0 || key > 255) {
            cdc_write("ERR,SETKEY_RANGE\n");
            return;
        }
        cfg.keymap[idx] = (uint8_t)key;
        save_config();
        cdc_write("OK,SETKEY\n");
    } else {
        cdc_write("ERR,SETKEY_FORMAT\n");
    }
}

static void handle_pin_cmd(char *line) {
    unsigned player = 0, pin = 0;
    int offset = 8;
    if (strncmp(line, "RELAYPIN,", 9) == 0) offset = 9;
    else if (strncmp(line, "TRIGGERPIN,", 11) == 0) offset = 11;
    if (sscanf(line + offset, "%u,%u", &player, &pin) == 2 && pin <= 28) {
        bool is_coin = (strncmp(line, "COINPIN,", 8) == 0);
        bool is_trigger = (strncmp(line, "TRIGGERPIN,", 11) == 0);
        if (!is_coin && !is_trigger && player == 1) cfg.p1_relay_pin = (uint8_t)pin;
        else if (!is_coin && !is_trigger && player == 2) cfg.p2_relay_pin = (uint8_t)pin;
        else if (is_coin && player == 1) cfg.p1_coin_pin = (uint8_t)pin;
        else if (is_coin && player == 2) cfg.p2_coin_pin = (uint8_t)pin;
        else if (is_trigger && player == 1) cfg.p1_trigger_pin = (uint8_t)pin;
        else if (is_trigger && player == 2) cfg.p2_trigger_pin = (uint8_t)pin;
        else { cdc_write("ERR,PIN_PLAYER\n"); return; }
        configure_inputs();
        configure_relays();
        save_config();
        cdc_write("OK,PIN\n");
        send_config();
    } else cdc_write("ERR,PIN_FORMAT\n");
}

static void handle_relay(char *line) {
    unsigned player = 0, state = 1;
    if (strncmp(line, "RELAYTEST,", 10) == 0) {
        if (sscanf(line + 10, "%u", &player) == 1) state = 1;
    } else if (strncmp(line, "RELAY,", 6) == 0) {
        if (sscanf(line + 6, "%u,%u", &player, &state) < 1) player = 0;
    }
    uint32_t now = ms_now();
    if (player == 1) {
        p1_test_until_ms = state ? now + RELAY_TEST_MS : 0;
        cdc_write("OK,RELAY,P1\n");
    } else if (player == 2) {
        p2_test_until_ms = state ? now + RELAY_TEST_MS : 0;
        cdc_write("OK,RELAY,P2\n");
    } else cdc_write("ERR,RELAY_PLAYER\n");
}

static void handle_line(char *line) {
    if (strcmp(line, "PING") == 0) {
        cdc_write("HELLO,KEYBOARD,GT_GAME_CONTROLER_CONTROLLER,V023\n");
    } else if (strcmp(line, "GET") == 0) {
        send_status();
    } else if (strcmp(line, "GETCFG") == 0) {
        send_config();
    } else if (strcmp(line, "MAP") == 0) {
        send_map();
    } else if (strncmp(line, "SETCFG,", 7) == 0) {
        handle_setcfg(line);
    } else if (strncmp(line, "SETKEY,", 7) == 0) {
        handle_setkey(line);
    } else if (strncmp(line, "RELAYPIN,", 9) == 0 || strncmp(line, "COINPIN,", 8) == 0 || strncmp(line, "TRIGGERPIN,", 11) == 0) {
        handle_pin_cmd(line);
    } else if (strncmp(line, "RELAYTEST,", 10) == 0 || strncmp(line, "RELAY,", 6) == 0) {
        handle_relay(line);
    } else if (strcmp(line, "RESETCFG") == 0) {
        default_config();
        configure_inputs();
        configure_relays();
        save_config();
        cdc_write("OK,RESETCFG\n");
    }
}

static void poll_cdc(void) {
    static char line[128];
    static uint8_t pos = 0;
    while (tud_cdc_available()) {
        char c;
        tud_cdc_read(&c, 1);
        if (c == '\n' || c == '\r') {
            if (pos) {
                line[pos] = 0;
                handle_line(line);
                pos = 0;
            }
        } else if (pos < sizeof(line) - 1) {
            line[pos++] = c;
        }
    }
}

static void send_keyboard_report(void) {
    if (!tud_hid_ready()) return;

    uint8_t keycode[6] = {0};
    uint8_t count = 0;

    for (uint i = 0; i < PIN_COUNT && count < 6; i++) {
        if (cfg.keymap[i] != 0 && pressed_pin(pins[i].pin)) {
            keycode[count++] = cfg.keymap[i];
        }
    }

    tud_hid_keyboard_report(REPORT_ID_KEYBOARD, 0, keycode);
}

static void update_relay_logic(void) {
    uint32_t now = ms_now();
    bool p1_coin = p1_coin_pressed();
    bool p2_coin = p2_coin_pressed();
    bool p1_trigger = p1_trigger_pressed();
    bool p2_trigger = p2_trigger_pressed();

    if (p1_coin) {
        p1_game_active = true;
        p1_last_trigger_ms = now;
    }
    if (p2_coin) {
        p2_game_active = true;
        p2_last_trigger_ms = now;
    }

    if ((int32_t)(p1_test_until_ms - now) > 0) {
        set_p1_relay(true);
    } else if (p1_game_active) {
        if (p1_trigger) {
            p1_last_trigger_ms = now;
            set_p1_relay(true);
        } else {
            set_p1_relay(false);
        }
        if ((uint32_t)(now - p1_last_trigger_ms) > INACTIVE_TIMEOUT_MS) {
            p1_game_active = false;
            set_p1_relay(false);
        }
    } else {
        set_p1_relay(false);
    }

    if ((int32_t)(p2_test_until_ms - now) > 0) {
        set_p2_relay(true);
    } else if (p2_game_active) {
        if (p2_trigger) {
            p2_last_trigger_ms = now;
            set_p2_relay(true);
        } else {
            set_p2_relay(false);
        }
        if ((uint32_t)(now - p2_last_trigger_ms) > INACTIVE_TIMEOUT_MS) {
            p2_game_active = false;
            set_p2_relay(false);
        }
    } else {
        set_p2_relay(false);
    }
}

int main(void) {
    tusb_init();
    load_config();
    configure_inputs();
    configure_relays();

    uint32_t last_hid = 0;
    uint32_t last_status = 0;
    uint32_t last_logic = 0;
    while (1) {
        tud_task();
        poll_cdc();
        uint32_t now = ms_now();
        if (now - last_logic >= LOGIC_INTERVAL_MS) {
            last_logic = now;
            update_relay_logic();
        }
        if (now - last_hid >= HID_INTERVAL_MS) {
            last_hid = now;
            send_keyboard_report();
        }
        if (now - last_status >= STATUS_INTERVAL_MS) {
            last_status = now;
            send_status();
        }
    }
}
