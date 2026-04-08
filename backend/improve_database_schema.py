"""
Database Schema Improvements for Wildlife Surveillance Application
This script ensures the reports collection has all required fields and proper indexes
for optimal performance.
"""

from pymongo import MongoClient, IndexModel
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client.wildlife_offence_db
reports_collection = db.reports
users_collection = db.users
officials_collection = db.officials

def create_indexes():
    """Create necessary indexes for optimal performance"""
    print("Creating database indexes...")
    
    # Reports collection indexes
    report_indexes = [
        IndexModel([("user_id", 1)], name="user_id_index"),
        IndexModel([("created_at", -1)], name="created_at_index"),
        IndexModel([("status", 1)], name="status_index"),
        IndexModel([("severity", 1)], name="severity_index"),
        IndexModel([("offence_type", 1)], name="offence_type_index"),
        IndexModel([("location.lat", 1), ("location.lng", 1)], name="location_index"),
        IndexModel([("user_id", 1), ("created_at", -1)], name="user_created_index"),
        IndexModel([("severity", 1), ("created_at", -1)], name="severity_created_index"),
        IndexModel([("status", 1), ("created_at", -1)], name="status_created_index"),
    ]
    
    try:
        reports_collection.create_indexes(report_indexes)
        print("✅ Reports collection indexes created successfully")
    except Exception as e:
        print(f"❌ Error creating reports indexes: {e}")
    
    # Users collection indexes
    user_indexes = [
        IndexModel([("email", 1)], name="email_index", unique=True),
        IndexModel([("role", 1)], name="role_index"),
        IndexModel([("created_at", -1)], name="user_created_at_index"),
    ]
    
    try:
        users_collection.create_indexes(user_indexes)
        print("✅ Users collection indexes created successfully")
    except Exception as e:
        print(f"❌ Error creating users indexes: {e}")
    
    # Officials collection indexes
    official_indexes = [
        IndexModel([("email", 1)], name="official_email_index", unique=True),
        IndexModel([("created_at", -1)], name="official_created_at_index"),
    ]
    
    try:
        officials_collection.create_indexes(official_indexes)
        print("✅ Officials collection indexes created successfully")
    except Exception as e:
        print(f"❌ Error creating officials indexes: {e}")

def validate_report_schema():
    """Validate and update report documents to ensure they have all required fields"""
    print("Validating report schema...")
    
    # Get all reports that might be missing fields
    reports = list(reports_collection.find({}))
    updated_count = 0
    
    for report in reports:
        updates = {}
        
        # Ensure required fields exist
        if 'report_id' not in report:
            updates['report_id'] = str(report['_id'])
        
        if 'user_id' not in report:
            print(f"⚠️  Report {report['_id']} missing user_id")
            continue
        
        if 'status' not in report:
            updates['status'] = 'New'
        
        if 'severity' not in report:
            updates['severity'] = 'Low'
        
        if 'threat_level' not in report:
            updates['threat_level'] = 'LOW'
        
        # Ensure location object has required fields
        if 'location' not in report:
            updates['location'] = {
                'lat': 0,
                'lng': 0,
                'address': 'Location not available',
                'accuracy': None
            }
        else:
            location_updates = {}
            if 'accuracy' not in report['location']:
                location_updates['accuracy'] = None
            if 'timestamp' not in report['location']:
                location_updates['timestamp'] = None
            
            if location_updates:
                for k, v in location_updates.items():
                    updates[f'location.{k}'] = v
        
        # Ensure timestamp fields
        if 'created_at' not in report:
            updates['created_at'] = datetime.utcnow()
        
        if 'updated_at' not in report:
            updates['updated_at'] = datetime.utcnow()
        
        # Apply updates if any
        if updates:
            try:
                reports_collection.update_one(
                    {'_id': report['_id']},
                    {'$set': updates}
                )
                updated_count += 1
                print(f"📝 Updated report {report['_id']} with missing fields")
            except Exception as e:
                print(f"❌ Error updating report {report['_id']}: {e}")
    
    print(f"✅ Schema validation complete. Updated {updated_count} reports")

def create_sample_data():
    """Create sample data for testing if collections are empty"""
    print("Checking for sample data...")
    
    # Check if users exist
    user_count = users_collection.count_documents({})
    if user_count == 0:
        print("📝 Creating sample user...")
        sample_user = {
            'name': 'Test User',
            'email': 'user@example.com',
            'password': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LrUpm',  # 'password'
            'role': 'user',
            'phone': '+1234567890',
            'created_at': datetime.utcnow()
        }
        users_collection.insert_one(sample_user)
        print("✅ Sample user created")
    
    # Check if officials exist
    official_count = officials_collection.count_documents({})
    if official_count == 0:
        print("📝 Creating sample official...")
        sample_official = {
            'name': 'Forest Officer',
            'email': 'official@example.com',
            'password': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LrUpm',  # 'password'
            'role': 'official',
            'department': 'Forest Department',
            'badge_number': 'FD001',
            'phone': '+1234567891',
            'created_at': datetime.utcnow()
        }
        officials_collection.insert_one(sample_official)
        print("✅ Sample official created")

def get_database_stats():
    """Display database statistics"""
    print("\n📊 Database Statistics:")
    print(f"   Total Reports: {reports_collection.count_documents({})}")
    print(f"   Total Users: {users_collection.count_documents({})}")
    print(f"   Total Officials: {officials_collection.count_documents({})}")
    
    # Report breakdown
    status_breakdown = list(reports_collection.aggregate([
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]))
    
    severity_breakdown = list(reports_collection.aggregate([
        {'$group': {'_id': '$severity', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]))
    
    print("\n   Reports by Status:")
    for item in status_breakdown:
        print(f"     {item['_id']}: {item['count']}")
    
    print("\n   Reports by Severity:")
    for item in severity_breakdown:
        print(f"     {item['_id']}: {item['count']}")

def main():
    """Main function to run all database improvements"""
    print("🔧 Wildlife Surveillance Database Schema Improvements")
    print("=" * 50)
    
    try:
        create_indexes()
        validate_report_schema()
        create_sample_data()
        get_database_stats()
        
        print("\n✅ Database schema improvements completed successfully!")
        print("📋 The application now has:")
        print("   • Proper indexes for optimal query performance")
        print("   • Validated report schema with all required fields")
        print("   • Sample data for testing (if collections were empty)")
        print("   • Enhanced location tracking with GPS accuracy")
        
    except Exception as e:
        print(f"\n❌ Error during database improvements: {e}")
        raise
    
    finally:
        client.close()

if __name__ == "__main__":
    main()
