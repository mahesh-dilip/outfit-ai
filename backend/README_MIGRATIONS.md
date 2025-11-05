# Database Migrations with Alembic

## Setup Complete ✅

Alembic has been configured for managing database schema migrations safely.

## Configuration

- **alembic.ini**: Main configuration file
- **alembic/env.py**: Environment configuration (imports models from app_server.py)
- **alembic/versions/**: Migration scripts directory

## Common Commands

### Check Current Migration State
```bash
alembic current
```

### Create a New Migration (Auto-generate)
```bash
# After modifying models in app_server.py
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations (Upgrade)
```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific number of migrations
alembic upgrade +1

# Apply to specific revision
alembic upgrade <revision_id>
```

### Rollback Migrations (Downgrade)
```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### View Migration History
```bash
# Show migration history
alembic history

# Show history with more detail
alembic history --verbose
```

### View SQL Without Applying
```bash
# See SQL that would be executed
alembic upgrade head --sql
```

## Workflow for Schema Changes

### 1. Modify Models
Edit the SQLAlchemy models in `app_server.py`:
```python
# Example: Add a new column
class WardrobeItem(Base):
    # ... existing columns ...
    brand = Column(String, nullable=True)  # New column
```

### 2. Create Migration
```bash
alembic revision --autogenerate -m "Add brand column to wardrobe_items"
```

### 3. Review Generated Migration
Check the generated file in `alembic/versions/` to ensure it's correct.

### 4. Apply Migration
```bash
alembic upgrade head
```

### 5. Test
Verify the changes work correctly with your application.

## Best Practices

1. **Always Review Auto-generated Migrations**
   - Alembic's auto-generate is smart but not perfect
   - Check the generated migration before applying

2. **Test Migrations Both Ways**
   - Test `upgrade` AND `downgrade`
   - Ensure rollback works correctly

3. **One Logical Change Per Migration**
   - Keep migrations focused and atomic
   - Easier to debug and rollback

4. **Descriptive Migration Messages**
   - Use clear, descriptive names
   - Example: "Add user profile fields" not "Update users"

5. **Backup Before Major Migrations**
   - Always backup production database before migrations
   - Test on staging environment first

6. **Never Edit Applied Migrations**
   - Once a migration is applied, create a new migration for changes
   - Editing applied migrations breaks history

## Troubleshooting

### "Target database is not up to date"
```bash
# Check current state
alembic current

# Stamp database to specific revision
alembic stamp head
```

### Migration Not Detected
```bash
# Ensure models are imported in alembic/env.py
# Check that Base.metadata includes all models
```

### Rollback Failed
```bash
# Check the down ward
grade() function in the migration
# May need to manually fix database state
```

## Example: Adding a New Table

1. Add model to `app_server.py`:
```python
class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    bio = Column(String, nullable=True)
```

2. Create migration:
```bash
alembic revision --autogenerate -m "Add user_profiles table"
```

3. Review and apply:
```bash
# Review the generated migration
cat alembic/versions/XXXX_add_user_profiles_table.py

# Apply it
alembic upgrade head
```

## Integration with Application

The application automatically uses the latest schema. After running migrations:

1. Restart the application
2. New schema changes are active
3. No code changes needed (if only adding optional fields)

## Production Deployment

### Pre-deployment Checklist
- [ ] Test migrations on staging database
- [ ] Backup production database
- [ ] Review all SQL that will be executed
- [ ] Plan rollback strategy
- [ ] Test application with new schema

### Deployment Process
```bash
# 1. Backup database
cp outfitai.db outfitai.db.backup

# 2. Apply migrations
alembic upgrade head

# 3. Restart application
# (Application automatically uses new schema)

# 4. If issues, rollback
alembic downgrade -1
```

## Current Schema

### Tables
1. **users**
   - id (PK)
   - email (unique)
   - hashed_password

2. **wardrobe_items**
   - id (PK)
   - title
   - description
   - category
   - color
   - image_url
   - owner_id (FK → users.id)

3. **saved_outfits**
   - id (PK)
   - name
   - reason
   - item_ids (comma-separated string)
   - owner_id (FK → users.id)

## Future Improvements

Planned schema enhancements (will use migrations):
- Add timestamps (created_at, updated_at) to all tables
- Add wear_count, last_worn_date to wardrobe_items
- Convert item_ids in saved_outfits to proper JSON array
- Add indexes for performance
- Add user_profiles table for extended user data

---

**Alembic Version:** 1.17.1  
**Last Updated:** November 5, 2025

