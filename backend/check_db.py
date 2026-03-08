import json
from pymongo import MongoClient

def main():
    client = MongoClient('mongodb://localhost:27017/')
    db = client.wildlife_offence_db
    
    users = list(db.users.find({}, {'_id': 1, 'name': 1, 'email': 1}))
    reports = list(db.reports.find({}, {'_id': 1, 'user_id': 1, 'user_name': 1}))
    
    print("--- USERS ---")
    for u in users:
        print(f"ID: {u['_id']} (type: {type(u['_id']).__name__}), Name: {u.get('name')}, Email: {u.get('email')}")
        
    print("\n--- REPORTS ---")
    for r in reports:
        print(f"Report ID: {r['_id']}, User ID inside report: {r.get('user_id')} (type: {type(r.get('user_id')).__name__}), User Name: {r.get('user_name')}")

if __name__ == '__main__':
    main()
