# socialsim/clock.py — the monotone social clock (SPEC-social §5).
REBASE_AFTER = 30 * 86400

class SocialClock:
    """sim_now = max(device_now, high_water). A device clock set back freezes the simulation until real time catches up, so
    no displayed value can rewind. A clock that was more than 30 days in the future and got repaired triggers ONE rebase."""
    def __init__(self, high_water=0.0):
        self.high_water = float(high_water)
        self.rebased = 0

    def now(self, device_now):
        d = float(device_now)
        if self.high_water - d > REBASE_AFTER:
            self.high_water = d
            self.rebased += 1
            return d
        if d > self.high_water:
            self.high_water = d
        return self.high_water
