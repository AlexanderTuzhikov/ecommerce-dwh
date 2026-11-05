import os
import pandas as pd

# Папка с CSV-файлами
folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# Читаем все CSV из папки
data = {}
for file in os.listdir(folder):
    if file.endswith(".csv"):
        data[file] = pd.read_csv(os.path.join(folder, file))

print("Найдено файлов:", len(data))
for file in data:
    print(" -", file)

# =====================================================
# ЧАСТЬ 1. ПРОФИЛЬ КАЖДОГО ФАЙЛА
# =====================================================
for file, df in data.items():
    print()
    print("=" * 70)
    print("ФАЙЛ:", file)
    print("=" * 70)
    print("Строк:", len(df), ", колонок:", df.shape[1])
    print("Полных дублей строк:", df.duplicated().sum())

    # Профиль каждой колонки
    print()
    print("Профиль колонок:")
    for col in df.columns:
        s = df[col]
        nulls = s.isna().sum()
        print()
        print("  " + col, "| тип:", s.dtype, "| пропусков:", nulls,
              "(" + str(round(nulls / len(df) * 100, 1)) + " %)",
              "| уникальных:", s.nunique())

        # Числовая колонка: диапазон и отрицательные значения
        if pd.api.types.is_numeric_dtype(s):
            print("     мин:", s.min(), "| макс:", s.max(), "| среднее:", round(s.mean(), 2),
                  "| меньше нуля:", (s < 0).sum(), "| нулей:", (s == 0).sum())
        # Текстовая колонка: самые частые значения и лишние пробелы
        else:
            top = s.value_counts().head(3)
            top_text = ""
            for value, cnt in top.items():
                top_text = top_text + str(value) + " (" + str(cnt) + "), "
            print("     частые значения:", top_text)
            text = s.dropna().astype(str)
            spaces = (text != text.str.strip()).sum()
            if spaces > 0:
                print("     ВНИМАНИЕ: значений с лишними пробелами:", spaces)

        # Особенности колонки (для файла из одной строки не нужны)
        if len(df) > 1:
            if s.nunique() == 1:
                print("     ВНИМАНИЕ: во всех строках одно значение")
            if nulls > 0 and nulls / len(df) > 0.5:
                print("     ВНИМАНИЕ: больше половины значений пустые")
            if s.nunique() == len(df) - nulls and nulls == 0:
                print("     все значения уникальны: возможный ключ")
            if "date" in col and not pd.api.types.is_numeric_dtype(s):
                print("     ВНИМАНИЕ: дата хранится как текст, нужно привести к date")
            if "time" in col and not pd.api.types.is_numeric_dtype(s):
                print("     ВНИМАНИЕ: время хранится как текст")

    # Колонки с датой: период и некорректные значения
    for col in df.columns:
        if "date" in col and not pd.api.types.is_numeric_dtype(df[col]):
            dates = pd.to_datetime(df[col], errors="coerce")
            print()
            print("Период в колонке", col + ":", dates.min().date(), "-", dates.max().date(),
                  "| не распознано как дата:", dates.isna().sum() - df[col].isna().sum())

    # Ключи: если нет уникальной колонки, проверяем пару *_id
    id_cols = [c for c in df.columns if c.endswith("_id")]
    has_unique = False
    for c in id_cols:
        if df[c].is_unique:
            has_unique = True
    if not has_unique and len(id_cols) >= 2:
        pair = id_cols[:2]
        print()
        print("Уникального ключа нет. Дублей по паре", pair, ":", df.duplicated(subset=pair).sum())

# =====================================================
# ЧАСТЬ 2. СВЯЗИ МЕЖДУ ФАЙЛАМИ
# =====================================================
print()
print("=" * 70)
print("СВЯЗИ МЕЖДУ ФАЙЛАМИ")
print("=" * 70)

names = list(data.keys())
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a = data[names[i]]
        b = data[names[j]]
        # общие колонки с id
        common = [c for c in a.columns if c in b.columns and c.endswith("_id")]
        for c in common:
            a_not_in_b = (~a[c].isin(b[c])).sum()
            b_not_in_a = (~b[c].isin(a[c])).sum()
            print(names[i], "<->", names[j], "по", c)
            print("   строк в первом без пары во втором:", a_not_in_b)
            print("   строк во втором без пары в первом:", b_not_in_a)

# =====================================================
# ЧАСТЬ 3. СРАВНЕНИЕ СУММ В ЗАКАЗАХ И ПОЗИЦИЯХ
# =====================================================
print()
print("=" * 70)
print("СУММЫ В ЗАКАЗАХ И В ПОЗИЦИЯХ ЗАКАЗОВ")
print("=" * 70)

orders = data.get("ecommerce_sales_customer_analytics_150k.csv")
items = data.get("order_items.csv")

if orders is not None and items is not None:
    for col in ["quantity", "gross_sales", "net_sales", "profit"]:
        if col in orders.columns and col in items.columns:
            # сумма по позициям для каждого заказа
            items_sum = items.groupby("order_id")[[col]].sum()
            items_sum = items_sum.rename(columns={col: "items_value"})
            m = orders[["order_id", col]].merge(items_sum, on="order_id")
            diff = (m[col] - m["items_value"]).abs()
            print(col + ": заказов, где сумма по заказу не равна сумме позиций:", (diff >= 0.05).sum(),
                  "из", len(m))
            print("   итого по заказам:", round(m[col].sum(), 2),
                  "| итого по позициям:", round(m["items_value"].sum(), 2))

    # Статусы заказов
    print()
    print("Статусы заказов:")
    print(orders["order_status"].value_counts())
    print()
    print("В каких статусах заказов пустые значения (по колонкам с пропусками):")
    for col in orders.columns:
        if orders[col].isna().sum() > 0:
            print("  " + col + ":")
            counts = orders[orders[col].isna()]["order_status"].value_counts()
            for status, cnt in counts.items():
                print("      ", status, int(cnt))

print()
print("Профилирование завершено")