"""Contains functions needed for calculating drop chances."""
import math
STREAK_INCREASE = 11.58

def truncate_decimals(num):
    """Replaced my old function with a builtin, can decide on significance."""
    return "{0:.4g}".format(num)

def pet_chance(droprate, threshold, killcount):
    """Calls recursive pet_chance_counter function to determine chance of not getting pet."""
    def pet_chance_counter(droprate, threshold, killcount, threshold_counter):
        """Calculates chance of not getting pet recursively."""
        if killcount < threshold or threshold_counter == 9:
            return math.pow((1-(threshold_counter/droprate)), killcount)
        chance = math.pow((1-(threshold_counter/droprate)), threshold)
        killcount = killcount - threshold
        threshold_counter += 1
        return chance*pet_chance_counter(droprate, threshold, killcount, threshold_counter)
    chance = pet_chance_counter(droprate, threshold, killcount, 1)
    chance *= 100
    return truncate_decimals(chance)

def droprate_reply(match):
    """Returns pet droprate info for normal mode and hard mode."""
    boss = match.group(1)
    boss_entry = DROPRATES[boss]
    pet_info = boss_entry.get("pet")
    if pet_info is None:
        return f"No pet information listed for {boss}."
    pet_hm_info = boss_entry.get("pet (hm)")
    if boss == "telos":
        out_msg = (f"With <100% enrage, Tess has droprate 1/{pet_info[0]} and threshold "
                   f"{pet_info[1]}. With >100% enrage, Tess has droprate "
                   f"1/{pet_hm_info[0]} and threshold {pet_hm_info[1]}.")
    else:
        out_msg = (f"The pet from {boss} has droprate 1/{pet_info[0]} and threshold "
                   f"{pet_info[1]}.")
        if pet_hm_info is not None:
            out_msg += (f"The pet from hardmode {boss} has droprate 1/{pet_hm_info[0]} and "
                        f"threshold {pet_hm_info[1]}.")
    return out_msg

def chance_helper(match, hardmode):
    """Returns pet chance with the given killcount."""
    boss = match.group(1)
    boss_entry = DROPRATES[boss]
    pet_info = boss_entry.get("pet")
    if pet_info is None:
        return f"No pet information listed for {boss}."
    pet_hm_info = boss_entry.get("pet (hm)")
    killcount = int(match.group(2))
    if boss == "telos":
        chance = pet_chance(pet_hm_info[0], pet_hm_info[1], killcount)
        out_msg = f"Your chance of not getting Tess by now is: {chance}%"
    else:
        if hardmode:
            if pet_hm_info is None:
                out_msg = "No difference in pet chance, using normal mode.\n"
                out_msg += chance_helper(match, 0)
            else:
                chance = pet_chance(pet_hm_info[0], pet_hm_info[1], killcount)
                out_msg = (f"Your chance of not getting the pet by now in hardmode "
                           f"is: {chance}%")
        else:
            chance = pet_chance(pet_info[0], pet_info[1], killcount)
            out_msg = f"Your chance of not getting the pet by now is: {chance}%"
    return out_msg

def chance_reply(match):
    """Calls chance_helper and specifies normal mode."""
    return chance_helper(match, 0)

def hm_chance_reply(match):
    """Calls chance_helper and specifies hard mode."""
    return chance_helper(match, 1)

def manual_reply(match):
    """Manually calculates pet chance with given threshold and droprate."""
    droprate = int(match.group(1))
    threshold = int(match.group(2))
    killcount = int(match.group(3))
    if droprate < 1:
        out_msg = "Invalid droprate (use the denominator)."
    elif threshold < 0:
        out_msg = "Invalid threshold."
    elif killcount < 0:
        out_msg = "Invalid killcount."
    else:
        chance = pet_chance(droprate, threshold, killcount)
        out_msg = f"Your chance of not getting the pet by now is: {chance}%"
    return out_msg

def telos(enrage, streak, lotd):
    """Returns the drop chance at a given enrage and streak, with or without LotD."""
    denominator = math.floor(10000.0/(10+0.25*(enrage+25*lotd)+3*streak))
    cap = 9
    if denominator < cap:
        return 1.0/cap
    return 1/denominator

def expected_uniques(start_enrage, end_enrage):
    """Given a start enrage and end enrage, returns expected number of uniques and kills."""
    streak_total = math.ceil((end_enrage-start_enrage)/STREAK_INCREASE)
    sum_of_expectations_lotd = 0.0
    sum_of_expectations_no_lotd = 0.0
    for i in range(1, streak_total + 1):
        enrage = start_enrage + STREAK_INCREASE*i
        streak = i
        sum_of_expectations_lotd += telos(enrage, streak, 1)
        sum_of_expectations_no_lotd += telos(enrage, streak, 0)
    sum_of_expectations_no_lotd = truncate_decimals(sum_of_expectations_no_lotd)
    sum_of_expectations_lotd = truncate_decimals(sum_of_expectations_lotd)
    return (sum_of_expectations_no_lotd, sum_of_expectations_lotd, streak_total)

def kills_until_unique(start_enrage):
    """Given a start enrage, return the expected number of kills until a unique is obtained."""
    expected_uniques_lotd = 0.0
    expected_uniques_no_lotd = 0.0
    streak = 0
    while expected_uniques_lotd <= 1:
        enrage = start_enrage + STREAK_INCREASE*streak
        expected_uniques_lotd += telos(enrage, streak, 1)
        streak += 1
    kills_for_lotd_unique = streak
    streak = 0
    while expected_uniques_no_lotd <= 1:
        enrage = start_enrage + STREAK_INCREASE*streak
        expected_uniques_lotd += telos(enrage, streak, 1)
        expected_uniques_no_lotd += telos(enrage, streak, 0)
        streak += 1
    kills_for_no_lotd_unique = streak
    return (kills_for_no_lotd_unique, kills_for_lotd_unique)

def bounds_reply(match):
    """Returns data on enrage bounds queries."""
    start_enrage = int(match.group(1))
    end_enrage = int(match.group(2))
    if start_enrage > end_enrage:
        return "Start enrage must be less than end enrage."
    (no_lotd, lotd, streak_total) = expected_uniques(start_enrage, end_enrage)
    out_msg = (f"Streaking from {start_enrage}% to {end_enrage}%:\n"
               f"Expected number of kills: {streak_total}\n"
               f"Expected uniques: {no_lotd} without LotD, {lotd} with LotD.")
    return out_msg

def start_reply(match):
    """Returns data on start enrage queries."""
    out_msg = ""
    start_enrage = int(match.group(1))
    if start_enrage > 4000:
        out_msg = "Using an enrage of 4000 (max chance).\n"
        start_enrage = 4000
    (no_lotd, lotd) = kills_until_unique(start_enrage)
    out_msg += (f"Streaking from {start_enrage}%:\n"
                f"Expected kills until unique: {no_lotd} without LotD, "
                f"{lotd} with LotD.")
    return out_msg

def unique_chance_reply(match):
    """Returns data on individual chance queries."""
    out_msg = ""
    enrage = int(match.group(1))
    streak = int(match.group(2))
    if enrage > 4000:
        out_msg = "Using an enrage of 4000 (max chance).\n"
        enrage = 4000
    no_lotd = telos(enrage, streak, 0)
    lotd = telos(enrage, streak, 1)
    out_msg += (f"A kill with enrage {enrage}% and streak {streak}:\n"
                f"Unique chance: 1/{int(1/no_lotd)} without LotD, "
                f"1/{int(1/lotd)} with LotD.")
    return out_msg
