"""Seed database from YAML files in data/seeds/."""
import os
import glob
import json
from .database import SessionLocal, engine, Base
from .models import TestCase, AuditLog
from .services.importer import parse_yaml_seed


def seed_from_directory(seeds_dir: str, reset: bool = False) -> dict:
    """Load all YAML seed files from a directory into the database."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if reset:
        db.query(TestCase).delete()
        db.commit()

    total_created, total_updated, total_errors = 0, 0, 0
    file_stats = []

    for yaml_path in sorted(glob.glob(os.path.join(seeds_dir, "*.yaml"))):
        filename = os.path.basename(yaml_path)
        with open(yaml_path) as f:
            content = f.read()

        test_cases = parse_yaml_seed(content)
        created, updated, errors = 0, 0, 0

        for tc_data in test_cases:
            try:
                existing = db.query(TestCase).filter(TestCase.id == tc_data["id"]).first()
                if existing:
                    for k, v in tc_data.items():
                        if v is not None:
                            setattr(existing, k, v)
                    updated += 1
                else:
                    db.add(TestCase(**tc_data))
                    created += 1
            except Exception as e:
                errors += 1
                print(f"  ERROR {tc_data.get('id', '?')}: {e}")

        db.commit()
        total_created += created
        total_updated += updated
        total_errors += errors
        file_stats.append({"file": filename, "created": created, "updated": updated, "errors": errors})
        print(f"  {filename}: +{created} new, ~{updated} updated, {errors} errors")

    db.add(AuditLog(
        entity_type="seed", entity_id="all",
        action="seed", new_value=json.dumps({"created": total_created, "updated": total_updated})
    ))
    db.commit()
    db.close()

    return {
        "total_created": total_created,
        "total_updated": total_updated,
        "total_errors": total_errors,
        "files": file_stats,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed database from YAML files")
    parser.add_argument("--seeds-dir", default="data/seeds", help="Directory containing YAML seed files")
    parser.add_argument("--reset", action="store_true", help="Delete all existing test cases before seeding")
    args = parser.parse_args()

    print(f"Seeding from {args.seeds_dir}...")
    stats = seed_from_directory(args.seeds_dir, reset=args.reset)
    print(f"\nDone: {stats['total_created']} created, {stats['total_updated']} updated, {stats['total_errors']} errors")
