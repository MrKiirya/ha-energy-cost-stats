import { describe, expect, it } from "vitest";
import {
  autoGrouping,
  currentPeriod,
  dayCount,
  exclusiveEnd,
  groupingAllowed,
  isValidDate,
  periodKind,
  presetPeriod,
  requestEnd,
  shiftPeriod,
  todayIn,
} from "../src/period";

// 2026-11-06 is a Friday.
const TODAY = "2026-11-06";

describe("presetPeriod", () => {
  it.each([
    ["today", "2026-11-06", "2026-11-06"],
    ["yesterday", "2026-11-05", "2026-11-05"],
    ["this_week", "2026-11-02", "2026-11-08"],
    ["last_week", "2026-10-26", "2026-11-01"],
    ["this_month", "2026-11-01", "2026-11-30"],
    ["last_month", "2026-10-01", "2026-10-31"],
    ["this_quarter", "2026-10-01", "2026-12-31"],
    ["this_year", "2026-01-01", "2026-12-31"],
    ["now-7d", "2026-10-31", "2026-11-06"],
    ["now-30d", "2026-10-08", "2026-11-06"],
    ["now-12m", "2025-12-01", "2026-11-30"],
  ] as const)("%s", (preset, start, end) => {
    expect(presetPeriod(preset, TODAY)).toEqual({ start, end });
  });

  it("this_week on a Monday and a Sunday", () => {
    expect(presetPeriod("this_week", "2026-11-02")).toEqual({
      start: "2026-11-02",
      end: "2026-11-08",
    });
    expect(presetPeriod("this_week", "2026-11-08")).toEqual({
      start: "2026-11-02",
      end: "2026-11-08",
    });
  });

  it("last_month in January crosses the year", () => {
    expect(presetPeriod("last_month", "2026-01-15")).toEqual({
      start: "2025-12-01",
      end: "2025-12-31",
    });
  });

  it("this_quarter for the first month of a quarter", () => {
    expect(presetPeriod("this_quarter", "2026-04-01")).toEqual({
      start: "2026-04-01",
      end: "2026-06-30",
    });
  });
});

describe("periodKind", () => {
  it.each([
    [{ start: "2026-11-06", end: "2026-11-06" }, "day"],
    [{ start: "2026-11-02", end: "2026-11-08" }, "week"],
    [{ start: "2026-11-03", end: "2026-11-09" }, "days"],
    [{ start: "2026-02-01", end: "2026-02-28" }, "month"],
    [{ start: "2026-10-01", end: "2026-12-31" }, "quarter"],
    [{ start: "2026-11-01", end: "2027-01-31" }, "months"],
    [{ start: "2026-01-01", end: "2026-12-31" }, "year"],
    [{ start: "2025-12-01", end: "2026-11-30" }, "months"],
    [{ start: "2026-11-01", end: "2026-11-15" }, "days"],
  ] as const)("%j is %s", (period, kind) => {
    expect(periodKind(period)).toBe(kind);
  });
});

describe("shiftPeriod", () => {
  it("moves a day by one day", () => {
    expect(shiftPeriod({ start: TODAY, end: TODAY }, -1)).toEqual({
      start: "2026-11-05",
      end: "2026-11-05",
    });
    expect(shiftPeriod({ start: "2026-12-31", end: "2026-12-31" }, 1)).toEqual({
      start: "2027-01-01",
      end: "2027-01-01",
    });
  });

  it("moves a week by one week", () => {
    expect(shiftPeriod({ start: "2026-11-02", end: "2026-11-08" }, -1)).toEqual({
      start: "2026-10-26",
      end: "2026-11-01",
    });
  });

  it("moves a month by one month, keeping month ends", () => {
    expect(shiftPeriod({ start: "2026-03-01", end: "2026-03-31" }, -1)).toEqual({
      start: "2026-02-01",
      end: "2026-02-28",
    });
    expect(shiftPeriod({ start: "2026-01-01", end: "2026-01-31" }, 1)).toEqual({
      start: "2026-02-01",
      end: "2026-02-28",
    });
    expect(shiftPeriod({ start: "2024-01-01", end: "2024-01-31" }, 1)).toEqual({
      start: "2024-02-01",
      end: "2024-02-29",
    });
  });

  it("moves a quarter by three months and a year by twelve", () => {
    expect(shiftPeriod({ start: "2026-10-01", end: "2026-12-31" }, 1)).toEqual({
      start: "2027-01-01",
      end: "2027-03-31",
    });
    expect(shiftPeriod({ start: "2026-01-01", end: "2026-12-31" }, -1)).toEqual({
      start: "2025-01-01",
      end: "2025-12-31",
    });
  });

  it("moves a custom range by its length in days", () => {
    expect(shiftPeriod({ start: "2026-11-01", end: "2026-11-10" }, -1)).toEqual({
      start: "2026-10-22",
      end: "2026-10-31",
    });
  });

  it("ignores DST (calendar dates only)", () => {
    // Europe: DST ends on 2026-10-25.
    expect(shiftPeriod({ start: "2026-10-25", end: "2026-10-25" }, 1)).toEqual({
      start: "2026-10-26",
      end: "2026-10-26",
    });
  });
});

describe("currentPeriod", () => {
  it.each([
    [{ start: "2026-01-03", end: "2026-01-03" }, { start: TODAY, end: TODAY }],
    [
      { start: "2026-01-05", end: "2026-01-11" },
      { start: "2026-11-02", end: "2026-11-08" },
    ],
    [
      { start: "2026-01-01", end: "2026-01-31" },
      { start: "2026-11-01", end: "2026-11-30" },
    ],
    [
      { start: "2025-04-01", end: "2025-06-30" },
      { start: "2026-10-01", end: "2026-12-31" },
    ],
    [
      { start: "2024-01-01", end: "2024-12-31" },
      { start: "2026-01-01", end: "2026-12-31" },
    ],
    [
      { start: "2026-01-01", end: "2026-02-28" },
      { start: "2026-10-01", end: "2026-11-30" },
    ],
    [
      { start: "2026-01-01", end: "2026-01-10" },
      { start: "2026-10-28", end: "2026-11-06" },
    ],
  ])("%j -> %j", (period, expected) => {
    expect(currentPeriod(period, TODAY)).toEqual(expected);
  });
});

describe("helpers", () => {
  it("dayCount and exclusiveEnd", () => {
    expect(dayCount({ start: "2026-11-01", end: "2026-11-30" })).toBe(30);
    expect(exclusiveEnd({ start: "2026-11-01", end: "2026-11-30" })).toBe("2026-12-01");
  });

  it("isValidDate", () => {
    expect(isValidDate("2026-02-28")).toBe(true);
    expect(isValidDate("2026-02-30")).toBe(false);
    expect(isValidDate("2026-2-3")).toBe(false);
    expect(isValidDate("")).toBe(false);
  });

  it("todayIn uses the given time zone", () => {
    const instant = new Date("2026-11-06T22:30:00Z");
    expect(todayIn("UTC", instant)).toBe("2026-11-06");
    expect(todayIn("Europe/Moscow", instant)).toBe("2026-11-07");
    expect(todayIn("America/New_York", instant)).toBe("2026-11-06");
  });

  it("todayIn falls back on an unknown zone", () => {
    expect(todayIn("Not/AZone", new Date("2026-11-06T12:00:00Z"))).toMatch(
      /^\d{4}-\d{2}-\d{2}$/,
    );
  });

  it("autoGrouping and groupingAllowed", () => {
    expect(autoGrouping({ start: TODAY, end: TODAY })).toBe("hour");
    expect(autoGrouping({ start: "2026-11-01", end: "2026-11-30" })).toBe("day");
    expect(autoGrouping({ start: "2026-10-01", end: "2026-12-31" })).toBe("week");
    expect(autoGrouping({ start: "2026-01-01", end: "2026-12-31" })).toBe("month");
    expect(groupingAllowed("hour", { start: "2026-10-01", end: "2026-10-31" })).toBe(true);
    expect(groupingAllowed("hour", { start: "2026-10-01", end: "2026-11-01" })).toBe(false);
    expect(groupingAllowed("day", { start: "2026-01-01", end: "2026-12-31" })).toBe(true);
  });
});

describe("requestEnd", () => {
  const now = new Date("2026-11-06T12:34:00Z");

  it("past periods end at the exclusive end date", () => {
    expect(requestEnd({ start: "2026-10-01", end: "2026-10-31" }, "UTC", now)).toBe("2026-11-01");
  });

  it("a period containing today ends at the current local hour", () => {
    const month = { start: "2026-11-01", end: "2026-11-30" };
    expect(requestEnd(month, "UTC", now)).toBe("2026-11-06T12:00:00");
    expect(requestEnd(month, "Europe/Moscow", now)).toBe("2026-11-06T15:00:00");
    expect(requestEnd(month, "America/New_York", now)).toBe("2026-11-06T07:00:00");
  });

  it("uses the time zone's today", () => {
    const late = new Date("2026-11-06T22:10:00Z");
    // Already 2026-11-07 01:10 in Moscow: the 6th is past, the 7th has begun.
    expect(requestEnd({ start: "2026-11-06", end: "2026-11-06" }, "Europe/Moscow", late)).toBe(
      "2026-11-07",
    );
    expect(requestEnd({ start: "2026-11-07", end: "2026-11-07" }, "Europe/Moscow", late)).toBe(
      "2026-11-07T01:00:00",
    );
  });

  it("never asks for an empty range in the first hour of the period", () => {
    const midnight = new Date("2026-11-06T00:20:00Z");
    expect(requestEnd({ start: "2026-11-06", end: "2026-11-06" }, "UTC", midnight)).toBe(
      "2026-11-06T01:00:00",
    );
    expect(requestEnd({ start: "2026-11-01", end: "2026-11-30" }, "UTC", midnight)).toBe(
      "2026-11-06T00:00:00",
    );
  });

  it("falls back to the date for non-whole-hour offsets and unknown zones", () => {
    const month = { start: "2026-11-01", end: "2026-11-30" };
    expect(requestEnd(month, "Asia/Kolkata", now)).toBe("2026-12-01");
    expect(requestEnd(month, "Not/AZone", now)).toBe("2026-12-01");
  });
});
