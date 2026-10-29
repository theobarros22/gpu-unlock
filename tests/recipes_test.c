/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <string.h>
#include "../kernel/gpu_unlock/recipes.h"

int main(void)
{
	const struct gu_card *target = gu_card_find(0x25ec);
	const struct gu_card *ga106 = gu_card_find(0x2504);

	if (!target || target->chip != 0x177 || !ga106 ||
	    target->family != ga106->family) {
		fputs("GA107 25ec recipe missing or incorrect\n", stderr);
		return 1;
	}
	if (strcmp(target->family->fw->gsp, GU_FW_GSP_GA10X) ||
	    gu_card_find(0x25ed) || gu_card_find(0xffff)) {
		fputs("unexpected firmware or unsupported device accepted\n", stderr);
		return 1;
	}
	if (gu_card_allowed(0x25ec, 0x1028, 0x0bf8, false) ||
	    gu_card_allowed(0x25ec, 0x1028, 0x0bf9, true) ||
	    gu_card_allowed(0x25ec, 0x1029, 0x0bf8, true) ||
	    !gu_card_allowed(0x25ec, 0x1028, 0x0bf8, true) ||
	    !gu_card_allowed(0x2504, 0, 0, false)) {
		fputs("experimental admission policy incorrect\n", stderr);
		return 1;
	}
	puts("recipe selection passed");
	return 0;
}
