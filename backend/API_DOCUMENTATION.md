# Outfit AI API Documentation

**Version:** 2.0  
**Last Updated:** November 5, 2025

---

## Base URL

```
http://localhost:8000
```

## Authentication

All protected endpoints require JWT authentication.

### 1. Register a New User

**Endpoint:** `POST /users/`  
**Authentication:** None (public)

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "email": "user@example.com",
  "items": []
}
```

---

### 2. Login (Get Access Token)

**Endpoint:** `POST /token`  
**Authentication:** None (public)

**Request Body:** (form-urlencoded)
```
username=user@example.com&password=secure_password_123
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Usage:**
Add the token to subsequent requests:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### 3. Get Current User

**Endpoint:** `GET /users/me`  
**Authentication:** Required

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "items": [...]
}
```

---

## Wardrobe Items

### 4. Create Wardrobe Item

**Endpoint:** `POST /users/{user_id}/items/`  
**Authentication:** Required  
**Content-Type:** `multipart/form-data`

**Form Data:**
```
title: Blue Denim Jeans
description: Comfortable straight-leg jeans
category: Bottoms
color: Blue
image: <file>
```

**Response:** `201 Created`
```json
{
  "id": 123,
  "title": "Blue Denim Jeans",
  "description": "Comfortable straight-leg jeans",
  "category": "Bottoms",
  "color": "Blue",
  "image_url": "https://storage.googleapis.com/...",
  "owner_id": 1
}
```

**Notes:**
- Image is uploaded to Google Cloud Storage
- Item is added to vector index automatically
- Vector embedding is persisted

---

### 5. Get All Wardrobe Items

**Endpoint:** `GET /users/{user_id}/items/`  
**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": 123,
    "title": "Blue Denim Jeans",
    "description": "Comfortable straight-leg jeans",
    "category": "Bottoms",
    "color": "Blue",
    "image_url": "https://storage.googleapis.com/...",
    "owner_id": 1
  },
  ...
]
```

---

### 6. Get Single Wardrobe Item ✨ NEW

**Endpoint:** `GET /users/{user_id}/items/{item_id}`  
**Authentication:** Required

**Response:** `200 OK`
```json
{
  "id": 123,
  "title": "Blue Denim Jeans",
  "description": "Comfortable straight-leg jeans",
  "category": "Bottoms",
  "color": "Blue",
  "image_url": "https://storage.googleapis.com/...",
  "owner_id": 1
}
```

**Error Responses:**
- `404 Not Found` - Item doesn't exist
- `403 Forbidden` - Not authorized to access this item

---

### 7. Update Wardrobe Item ✨ NEW

**Endpoint:** `PUT /users/{user_id}/items/{item_id}`  
**Authentication:** Required  
**Content-Type:** `multipart/form-data`

**Form Data:** (all fields optional - partial update)
```
title: Updated Title
description: Updated description
category: Tops
color: Red
```

**Response:** `200 OK`
```json
{
  "id": 123,
  "title": "Updated Title",
  "description": "Updated description",
  "category": "Tops",
  "color": "Red",
  "image_url": "https://storage.googleapis.com/...",
  "owner_id": 1
}
```

**Notes:**
- Partial updates supported - only send fields you want to change
- Image update not yet supported (future feature)
- All fields are optional

**Error Responses:**
- `404 Not Found` - Item doesn't exist
- `403 Forbidden` - Not authorized to update this item

---

### 8. Delete Wardrobe Item ✨ NEW

**Endpoint:** `DELETE /users/{user_id}/items/{item_id}`  
**Authentication:** Required

**Response:** `200 OK`
```json
{
  "status": "success",
  "message": "Item 123 deleted successfully"
}
```

**Notes:**
- Item is permanently deleted from database
- Vector index is NOT updated (limitation - index cleanup coming)
- Image remains in GCS (cleanup coming)

**Error Responses:**
- `404 Not Found` - Item doesn't exist
- `403 Forbidden` - Not authorized to delete this item

---

### 9. Bulk Delete Wardrobe Items ✨ NEW

**Endpoint:** `DELETE /users/{user_id}/items/`  
**Authentication:** Required  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "item_ids": [123, 456, 789]
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "message": "Successfully deleted 3 items",
  "deleted_count": 3
}
```

**Notes:**
- Only deletes items owned by the user
- Returns count of actually deleted items
- If some IDs don't exist, only valid ones are deleted

---

## Outfit Recommendations

### 10. Get Outfit Recommendations

**Endpoint:** `POST /users/{user_id}/recommend-outfit`  
**Authentication:** Required  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "query": "casual outfit for coffee date"
}
```

**Response:** `200 OK`
```json
{
  "outfits": [
    {
      "outfit_name": "Casual Coffee Chic",
      "outfit_items": [123, 456, 789],
      "outfit_reason": "These items create a relaxed yet stylish look perfect for a coffee date. The blue jeans pair well with the white t-shirt, and the leather jacket adds sophistication."
    },
    {
      "outfit_name": "Weekend Comfort",
      "outfit_items": [124, 458, 791],
      "outfit_reason": "..."
    }
  ]
}
```

**Notes:**
- Uses RAG (Retrieval-Augmented Generation)
- Vector search finds relevant items from wardrobe
- AI generates outfits from relevant items only
- Returns 2-3 outfit suggestions

---

## Saved Outfits

### 11. Save Outfit

**Endpoint:** `POST /users/{user_id}/save-outfit`  
**Authentication:** Required  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "name": "Casual Coffee Chic",
  "reason": "Perfect for weekend coffee dates",
  "items": [123, 456, 789]
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "saved_outfit_id": 42
}
```

---

### 12. Get Saved Outfits

**Endpoint:** `GET /users/{user_id}/saved-outfits`  
**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": 42,
    "name": "Casual Coffee Chic",
    "reason": "Perfect for weekend coffee dates",
    "item_ids": "123,456,789"
  },
  ...
]
```

**Note:** `item_ids` is a comma-separated string (will be changed to array in future)

---

## Error Responses

All endpoints use consistent error format:

```json
{
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "Wardrobe item with id 999 not found",
  "details": {
    "resource": "Wardrobe item",
    "id": 999
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `AUTH_FAILED` | 401 | Authentication failed |
| `NOT_AUTHORIZED` | 403 | User not authorized for this action |
| `RESOURCE_NOT_FOUND` | 404 | Resource doesn't exist |
| `VALIDATION_ERROR` | 400 | Invalid input data |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `GCS_UPLOAD_FAILED` | 500 | Image upload failed |
| `VECTOR_DB_ERROR` | 500 | Vector search failed |
| `AI_GENERATION_FAILED` | 500 | AI generation failed |

---

## Example Workflows

### Complete User Flow

```bash
# 1. Register
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}'

# 2. Login
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=pass123"

# Save the access_token from response
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 3. Add item to wardrobe
curl -X POST "http://localhost:8000/users/1/items/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Blue Jeans" \
  -F "description=Denim jeans" \
  -F "category=Bottoms" \
  -F "color=Blue" \
  -F "image=@jeans.jpg"

# 4. Get all items
curl -X GET "http://localhost:8000/users/1/items/" \
  -H "Authorization: Bearer $TOKEN"

# 5. Update item
curl -X PUT "http://localhost:8000/users/1/items/123" \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Dark Blue Jeans" \
  -F "color=Dark Blue"

# 6. Get recommendations
curl -X POST "http://localhost:8000/users/1/recommend-outfit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"casual weekend outfit"}'

# 7. Delete item
curl -X DELETE "http://localhost:8000/users/1/items/123" \
  -H "Authorization: Bearer $TOKEN"

# 8. Bulk delete items
curl -X DELETE "http://localhost:8000/users/1/items/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_ids":[124,125,126]}'
```

---

## Rate Limiting

**Current:** None  
**Planned:** Coming in Phase 1 technical debt

---

## API Documentation UI

Visit the interactive API documentation:
```
http://localhost:8000/docs
```

This provides:
- Interactive API explorer
- Request/response examples
- Schema documentation
- Try-it-now functionality

---

## Changelog

### Version 2.0 (November 5, 2025)

**Added:**
- `GET /users/{user_id}/items/{item_id}` - Get single item
- `PUT /users/{user_id}/items/{item_id}` - Update item
- `DELETE /users/{user_id}/items/{item_id}` - Delete item
- `DELETE /users/{user_id}/items/` - Bulk delete
- Error handling with custom exceptions
- Structured logging for all operations
- Vector database persistence

**Changed:**
- All endpoints now require authentication
- Improved error responses with error codes
- Form parameters fixed (File → Form)

**Security:**
- JWT authentication on all protected endpoints
- Bcrypt password hashing
- Environment variables for secrets
- Authorization checks

### Version 1.0 (Initial)
- Basic CRUD for users and items
- Outfit recommendations
- Saved outfits
- No authentication (insecure)

---

## Future API Changes

### Coming Soon
- Image update for items
- Category filtering
- Pagination for items list
- Search/filter items by title, category, color
- Item metadata (brand, price, wear count)
- Favorite items

### Planned (Phase 3+)
- Rate limiting
- Webhook support
- Public API with OAuth
- GraphQL endpoint (maybe)

---

## Support

For issues or questions:
- Check `README_SECURITY.md` for authentication setup
- Check `README_LOGGING.md` for error codes
- View `/docs` for interactive documentation
- Review Linear project for roadmap

---

**API Version:** 2.0  
**Protocol:** REST  
**Authentication:** JWT Bearer Token  
**Data Format:** JSON (with multipart/form-data for file uploads)

