# Outfit AI Backend - Security Setup

## ✅ Phase 0 Security Fixes Completed

All critical security vulnerabilities have been addressed:

### 1. Environment Variables
- **Status:** ✅ Complete
- **Changes:**
  - Created `.env` file for all secrets
  - Created `env.example` template
  - Moved Gemini API key to `GEMINI_API_KEY`
  - Moved GCS credentials path to `GOOGLE_APPLICATION_CREDENTIALS`
  - Moved GCP project ID to `GCP_PROJECT_ID`

### 2. Password Hashing
- **Status:** ✅ Complete  
- **Changes:**
  - Replaced insecure `password + "notreallyhashed"` with bcrypt
  - Implemented proper password hashing using `passlib[bcrypt]`
  - Added password verification function

### 3. JWT Authentication
- **Status:** ✅ Complete
- **Changes:**
  - Created `auth.py` module with JWT token handling
  - Added `/token` endpoint for user login
  - Added `/users/me` endpoint to get current user
  - Protected all user-specific endpoints with authentication
  - Added authorization checks (users can only access their own data)

### 4. Form Parameter Bug
- **Status:** ✅ Complete
- **Changes:**
  - Fixed `/users/{user_id}/items/` endpoint
  - Changed `File(...)` to `Form(...)` for text fields (title, description, category, color)
  - Kept `File(...)` only for actual file upload (image)

### 5. Updated Dependencies
- **Status:** ✅ Complete
- **New packages:**
  - `python-dotenv` - Environment variable management
  - `python-jose[cryptography]` - JWT token handling
  - `passlib[bcrypt]` - Password hashing
  - `bcrypt` - Bcrypt algorithm
  - `python-multipart` - Form data handling
  - `pydantic-settings` - Settings management

## Setup Instructions

### 1. Install Dependencies
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
# Copy the example file
cp env.example .env

# Edit .env and add your actual credentials:
# - GEMINI_API_KEY: Your Google Gemini API key
# - GCS_BUCKET_NAME: Your Google Cloud Storage bucket name
# - GCP_PROJECT_ID: Your Google Cloud Project ID
# - JWT_SECRET_KEY: A secure random string (at least 32 characters)
```

### 3. Generate a Secure JWT Secret
```bash
# Generate a secure random string for JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Run the Server
```bash
uvicorn app_server:app --reload --port 8000
```

## API Authentication

### Register a New User
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure_password"}'
```

### Login (Get Access Token)
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=secure_password"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Use Authenticated Endpoints
```bash
# Add items (requires authentication)
curl -X POST "http://localhost:8000/users/1/items/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "title=Blue Jeans" \
  -F "description=Comfortable denim jeans" \
  -F "category=Bottoms" \
  -F "color=Blue" \
  -F "image=@/path/to/image.jpg"
```

## Security Best Practices

### ⚠️ Important: Before Production

1. **Rotate All Credentials:**
   - Generate a new Gemini API key
   - Create new GCS service account credentials
   - Never commit these to version control

2. **Update JWT Secret:**
   - Generate a strong random secret (at least 32 characters)
   - Keep it secret and never share it

3. **Update CORS Origins:**
   - Add your production frontend URL to `CORS_ORIGINS`
   - Remove localhost URLs in production

4. **Database:**
   - Consider migrating from SQLite to PostgreSQL for production
   - Implement database backups

5. **HTTPS:**
   - Always use HTTPS in production
   - Never send tokens over unsecured connections

## Protected Endpoints

All user-specific endpoints now require authentication:

- `POST /users/{user_id}/items/` - Create wardrobe item
- `GET /users/{user_id}/items/` - Get wardrobe items
- `POST /users/{user_id}/recommend-outfit` - Get outfit recommendations
- `POST /users/{user_id}/save-outfit` - Save outfit
- `GET /users/{user_id}/saved-outfits` - Get saved outfits

## Public Endpoints

These endpoints do not require authentication:

- `POST /users/` - Register new user
- `POST /token` - Login (get access token)
- `GET /docs` - API documentation

## Testing

To verify all security fixes are working:

```bash
# 1. Test import
python -c "from app_server import app; print('✅ App imports successfully')"

# 2. Start server
uvicorn app_server:app --reload

# 3. Test authentication flow
# - Register a user
# - Login to get token
# - Use token to access protected endpoints
```

## Troubleshooting

### "GEMINI_API_KEY environment variable is not set"
- Make sure `.env` file exists in the backend directory
- Check that `GEMINI_API_KEY` is set in `.env`
- Ensure `python-dotenv` is installed

### "GCS_BUCKET_NAME environment variable is not set"
- Add `GCS_BUCKET_NAME` to your `.env` file
- Set it to your actual GCS bucket name

### "Could not validate credentials"
- Your JWT token may have expired (default: 30 minutes)
- Login again to get a new token
- Check that `JWT_SECRET_KEY` is consistent

## Next Steps (Phase 1)

- [ ] Set up Alembic for database migrations
- [ ] Implement structured logging with Sentry
- [ ] Add comprehensive test coverage
- [ ] Persist vector database (FAISS → PostgreSQL/Pinecone)
- [ ] Clean up duplicate code and database backups

