import argparse
import csv
from pathlib import Path

from app.models.database import SessionLocal
from app.models.project import MaterialPrice


def ingest_csv(csv_path: Path):
    db = SessionLocal()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                price_low = None
                price_high = None
                if row.get("price"):
                    try:
                        price_low = float(row["price"])
                        price_high = price_low
                    except ValueError:
                        pass
                if row.get("price_low"):
                    try:
                        price_low = float(row["price_low"])
                    except ValueError:
                        pass
                if row.get("price_high"):
                    try:
                        price_high = float(row["price_high"])
                    except ValueError:
                        pass

                mat = MaterialPrice(
                    name=row.get("name", ""),
                    category=row.get("category", ""),
                    spec=row.get("spec", ""),
                    unit=row.get("unit", ""),
                    price_low=price_low,
                    price_high=price_high,
                    supplier_hint=row.get("supplier_hint", ""),
                    source=row.get("source", ""),
                )
                db.add(mat)
                count += 1

            db.commit()
            print(f"[OK] 导入 {count} 条材料价格数据")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="导入材料价格到 SQLite")
    parser.add_argument("--csv", required=True, help="CSV 文件路径")
    args = parser.parse_args()
    ingest_csv(Path(args.csv))


if __name__ == "__main__":
    main()
