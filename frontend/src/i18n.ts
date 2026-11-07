/** Card strings (English and Russian) and number/date formatting. */

import type { Grouping, Period, PeriodKind, Preset } from "./period";
import { periodKind } from "./period";

const EN = {
  title: "Energy cost",
  previous: "Previous",
  next: "Next",
  now: "Now",
  refresh: "Refresh",
  period: "Period",
  custom: "Custom period",
  from: "From",
  to: "To",
  apply: "Apply",
  grouping: "Grouping",
  "grouping.auto": "Auto",
  "grouping.hour": "Hours",
  "grouping.day": "Days",
  "grouping.week": "Weeks",
  "grouping.month": "Months",
  "grouping.hour_too_long": "Hours: up to 31 days",
  "preset.today": "Today",
  "preset.yesterday": "Yesterday",
  "preset.this_week": "This week",
  "preset.last_week": "Last week",
  "preset.this_month": "This month",
  "preset.last_month": "Last month",
  "preset.this_quarter": "This quarter",
  "preset.this_year": "This year",
  "preset.now-7d": "Last 7 days",
  "preset.now-30d": "Last 30 days",
  "preset.now-12m": "Last 12 months",
  device: "Device",
  total: "Total",
  kwh: "kWh",
  cost: "Cost",
  avg_price: "Avg. price",
  breakdown: "By period",
  breakdown_device: "Show",
  all_devices: "All devices",
  data_quality: "Data quality",
  loading: "Loading…",
  no_devices: "No energy sensors selected. Add them in the integration options.",
  no_plan: "No tariff plan covers this period: costs are unknown.",
  unpriced: "{hours} h before the first tariff plan are not priced.",
  "status.complete": "Complete",
  "status.estimated": "Contains estimated hours (spread over a data gap)",
  "status.partial": "Some hours are missing",
  "status.missing": "No data",
  "issue.estimated": "estimated",
  "issue.excluded_negative": "excluded (negative)",
  "issue.excluded_spike": "excluded (spike)",
  "statistics.no_statistics": "no statistics yet",
  "statistics.unsupported": "unsupported sensor",
  "error.not_loaded": "Energy Cost Stats is not set up or not loaded.",
  "error.invalid_period": "Invalid period.",
  "error.period_too_long": "The period is too long for this grouping.",
  "error.unknown_entity": "The card lists a sensor that is not selected in the integration.",
  "error.unknown_command": "The integration is not loaded (restart Home Assistant after installing).",
  "error.generic": "Could not load the report: {message}",
  "compare.title": "Tariff comparison",
  "compare.tariff": "Tariff",
  "compare.actual": "Actual",
  "compare.difference": "Difference",
  "compare.empty":
    "No tariffs to compare. Choose them in the integration options (Configure → Compare).",
  "compare.unpriced":
    "{hours} h not priced by this tariff — the difference covers only the priced hours",
  "compare.unpriced_actual":
    "{hours} h not priced by the actual schedule — the difference covers only the priced hours",
  "compare.error": "Could not load the comparison: {message}",
  "error.unknown_tariff": "A tariff in the comparison list is not defined in the integration.",
  "nested.title": "Measured inside {name}; not counted again in the total",
  "nested.note":
    "Indented rows are measured inside the device above them. The total counts their energy only for hours where the device above has no data.",
  coverage: "{measured} measured, {estimated} estimated, {excluded} excluded, {missing} missing of {expected} h",
} as const;

export type StringKey = keyof typeof EN;

const RU: Record<StringKey, string> = {
  title: "Стоимость электроэнергии",
  previous: "Назад",
  next: "Вперёд",
  now: "Сейчас",
  refresh: "Обновить",
  period: "Период",
  custom: "Свой период",
  from: "С",
  to: "По",
  apply: "Применить",
  grouping: "Группировка",
  "grouping.auto": "Авто",
  "grouping.hour": "По часам",
  "grouping.day": "По дням",
  "grouping.week": "По неделям",
  "grouping.month": "По месяцам",
  "grouping.hour_too_long": "По часам: до 31 дня",
  "preset.today": "Сегодня",
  "preset.yesterday": "Вчера",
  "preset.this_week": "Эта неделя",
  "preset.last_week": "Прошлая неделя",
  "preset.this_month": "Этот месяц",
  "preset.last_month": "Прошлый месяц",
  "preset.this_quarter": "Этот квартал",
  "preset.this_year": "Этот год",
  "preset.now-7d": "Последние 7 дней",
  "preset.now-30d": "Последние 30 дней",
  "preset.now-12m": "Последние 12 месяцев",
  device: "Устройство",
  total: "Итого",
  kwh: "кВт·ч",
  cost: "Сумма",
  avg_price: "Ср. цена",
  breakdown: "По периодам",
  breakdown_device: "Показать",
  all_devices: "Все устройства",
  data_quality: "Качество данных",
  loading: "Загрузка…",
  no_devices: "Не выбраны датчики энергии. Добавьте их в настройках интеграции.",
  no_plan: "Для этого периода нет тарифного плана: стоимость неизвестна.",
  unpriced: "{hours} ч до первого тарифного плана не оценены.",
  "status.complete": "Полные данные",
  "status.estimated": "Есть оценочные часы (распределены по пропуску)",
  "status.partial": "Часть часов отсутствует",
  "status.missing": "Нет данных",
  "issue.estimated": "оценка",
  "issue.excluded_negative": "исключено (отрицательное)",
  "issue.excluded_spike": "исключено (выброс)",
  "statistics.no_statistics": "статистики пока нет",
  "statistics.unsupported": "датчик не поддерживается",
  "error.not_loaded": "Energy Cost Stats не настроена или не загружена.",
  "error.invalid_period": "Неверный период.",
  "error.period_too_long": "Период слишком длинный для этой группировки.",
  "error.unknown_entity": "В карточке указан датчик, не выбранный в интеграции.",
  "error.unknown_command":
    "Интеграция не загружена (перезапустите Home Assistant после установки).",
  "error.generic": "Не удалось загрузить отчёт: {message}",
  "compare.title": "Сравнение тарифов",
  "compare.tariff": "Тариф",
  "compare.actual": "Фактически",
  "compare.difference": "Разница",
  "compare.empty":
    "Нет тарифов для сравнения. Выберите их в настройках интеграции (Настроить → Сравнение).",
  "compare.unpriced":
    "{hours} ч не оценены этим тарифом — разница учитывает только оценённые часы",
  "compare.unpriced_actual":
    "{hours} ч не оценены фактическим расписанием — разница учитывает только оценённые часы",
  "compare.error": "Не удалось загрузить сравнение: {message}",
  "error.unknown_tariff": "Тариф из списка сравнения не определён в интеграции.",
  "nested.title": "Измеряется внутри «{name}»; в итоге повторно не учитывается",
  "nested.note":
    "Строки со сдвигом измеряются внутри устройства выше. Итог учитывает их энергию только за часы, когда у устройства выше нет данных.",
  coverage:
    "{measured} измерено, {estimated} оценено, {excluded} исключено, {missing} нет из {expected} ч",
};

export class Strings {
  readonly locale: string;
  private readonly table: Record<StringKey, string>;

  constructor(language: string | undefined) {
    this.locale = language || "en";
    this.table = this.locale.toLowerCase().startsWith("ru") ? RU : EN;
  }

  t(key: StringKey, values: Record<string, string | number> = {}): string {
    return this.table[key].replace(/\{(\w+)\}/g, (_, name: string) =>
      name in values ? String(values[name]) : `{${name}}`,
    );
  }

  preset(preset: Preset): string {
    return this.t(`preset.${preset}` as StringKey);
  }

  grouping(grouping: Grouping | "auto"): string {
    return this.t(`grouping.${grouping}` as StringKey);
  }

  /** `null` (no data) → em dash; numbers keep their fixed decimals. */
  number(value: string | null | undefined, digits: number): string {
    if (value === null || value === undefined) return "—";
    return new Intl.NumberFormat(this.locale, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(Number(value));
  }

  money(
    value: string | null | undefined,
    currency: string | null,
    signed = false,
  ): string {
    if (value === null || value === undefined) return "—";
    if (currency) {
      try {
        return new Intl.NumberFormat(this.locale, {
          style: "currency",
          currency,
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
          ...(signed ? { signDisplay: "exceptZero" as const } : {}),
        }).format(Number(value));
      } catch {
        // Unknown currency code: plain number below.
      }
    }
    return signed
      ? new Intl.NumberFormat(this.locale, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
          signDisplay: "exceptZero",
        }).format(Number(value))
      : this.number(value, 2);
  }

  /** A difference with an explicit sign; `null` → dash. */
  signedMoney(amount: number | null, currency: string | null): string {
    return amount === null ? "—" : this.money(String(amount), currency, true);
  }

  /** A percentage with one decimal and an explicit sign; `null` → dash. */
  signedPercent(percent: number | null): string {
    if (percent === null) return "—";
    const text = new Intl.NumberFormat(this.locale, {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
      signDisplay: "exceptZero",
    }).format(percent);
    return `${text} %`;
  }

  /** Average price = cost / kWh, for display only. */
  avgPrice(cost: string | null, kwh: string | null): string {
    if (cost === null || kwh === null || Number(kwh) === 0) return "—";
    return this.number(String(Number(cost) / Number(kwh)), 2);
  }

  private date(date: string, options: Intl.DateTimeFormatOptions): string {
    return new Intl.DateTimeFormat(this.locale, { ...options, timeZone: "UTC" }).format(
      new Date(`${date}T00:00:00Z`),
    );
  }

  /** Header label of a period, e.g. "November 2026", "Q4 2026", "2 – 8 Nov 2026". */
  periodLabel(period: Period): string {
    const kind: PeriodKind = periodKind(period);
    switch (kind) {
      case "day":
        return this.date(period.start, { day: "numeric", month: "long", year: "numeric" });
      case "month":
        return this.date(period.start, { month: "long", year: "numeric" });
      case "quarter":
        return `Q${Math.floor(Number(period.start.slice(5, 7)) / 3) + 1} ${period.start.slice(0, 4)}`;
      case "year":
        return period.start.slice(0, 4);
      case "months":
        return `${this.date(period.start, { month: "short", year: "numeric" })} – ${this.date(period.end, { month: "short", year: "numeric" })}`;
      default: {
        const sameYear = period.start.slice(0, 4) === period.end.slice(0, 4);
        const start = this.date(period.start, {
          day: "numeric",
          month: "short",
          ...(sameYear ? {} : { year: "numeric" }),
        });
        const end = this.date(period.end, { day: "numeric", month: "short", year: "numeric" });
        return `${start} – ${end}`;
      }
    }
  }

  /** Row label of a report bucket (ISO datetime with offset, report time zone). */
  bucketLabel(start: string, grouping: Grouping): string {
    // The local wall-clock date and time are the text before the offset.
    const date = start.slice(0, 10);
    switch (grouping) {
      case "hour":
        return `${this.date(date, { day: "numeric", month: "short" })} ${start.slice(11, 16)}`;
      case "day":
        return this.date(date, { weekday: "short", day: "numeric", month: "short" });
      case "week":
        return this.date(date, { day: "numeric", month: "short", year: "numeric" });
      case "month":
        return this.date(date, { month: "long", year: "numeric" });
      default:
        return this.t("total");
    }
  }
}
