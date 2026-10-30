// Copyright (C) Windows GPU UNLOCK contributors. GPL-2.0-only.
/* HOST FIXTURE ONLY: public copy of the Dell G15 research identity so CI can
 * compile the Dell branches. Values match docs/RESULTADOS-WINDOWS-RTX3050.md;
 * the private profile next to machine-profile.h wins when present. This file
 * is not hardware evidence and does not make the profile reviewed. */
#pragma once

#define GU_PROFILE_NAME "DELL-G15-5530-RTX3050-6GB-GA107"
#define GU_BOARD_ID 0x25ec10deU
#define GU_BOARD_SUBSYSTEM 0x0bf81028U
#define GU_BAR0_BASE 0x74000000ULL
#define GU_BAR0_END 0x74ffffffULL
#define GU_DEVICE_MEMORY_SIZE 0x1800U

#define GU_TARGET_SEGMENT 0U
#define GU_TARGET_BUS 1U
#define GU_TARGET_DEVICE 0U
#define GU_TARGET_FUNCTION 0U

#define GU_GPU_FAMILY GU_GPU_FAMILY_GA107
#define GU_CHIP_ID 0xb77000a1U

/* Console topology: 0 = Intel UHD owns the console GOP; RTX 3050 has 0 display children in UEFI */
#define GU_CONSOLE_AGGREGATE 0
#define GU_CONSOLE_CHILD_COUNT 0
#define GU_NO_EDID_DRIVER 1

/* Console drivers are on Intel UHD, never on RTX 3050: zero placeholders compile cleanly and fail closed */
#define GU_CONSOLE_TEXT_SIZE 0U
#define GU_CONSOLE_TEXT_STOP 0U
#define GU_CONSOLE_TEXT_VERSION 0U
#define GU_CONSOLE_GFX_SIZE 0U
#define GU_CONSOLE_GFX_STOP 0U
#define GU_CONSOLE_GFX_VERSION 0U

/* NVIDIA GOP firmware fingerprint captured from Dell UEFI */
#define GU_NVGOP_VERSION 0x6001aU
#define GU_NVGOP_IMAGE_SIZE 0x26ee0U
#define GU_NVGOP_STOP 0x678U
#define GU_NVGOP_TEXT_BYTES 135459U
#define GU_NVGOP_TEXT_SHA256 "d622c6f68201bf0d79658a844b032e2ecadab7e457e9cd608c16ceadc74cb13b"

/* FWSEC / FRTS security container extracted by fwsec-locate on physical PROM.BIN */
#define GU_FWSEC_IMAGE_OFF 0x42d74U
#define GU_FWSEC_IMAGE_SIZE 0xea00U
#define GU_FWSEC_DMEM_SIZE 0x800U
#define GU_FWSEC_DATA_OFF 0xe200U
#define GU_FWSEC_PKC_OFF 0x5a4U
#define GU_FWSEC_UCODE_ID 9U
#define GU_FWSEC_ENGINE_MASK 0x400U
#define GU_FWSEC_SIG_COUNT 3U
#define GU_FWSEC_SIG_VERSIONS 7U
#define GU_FWSEC_SIG_BYTES 1152U
#define GU_PROM_SHA256 "e8f866920f803f61d67d805ff15ea46b1046c18c588def0f962fdcd8e937057c"
