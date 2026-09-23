# Cloud Kitchen Analytics API

## Authentication

POST /api/auth/signup
POST /api/auth/login

## Upload

POST /api/upload

## Analytics

GET /api/analytics/summary
GET /api/analytics/revenue
GET /api/analytics/orders

## Customers

GET /api/customers
GET /api/customers/segments

## Food Cost

GET /api/foodcost

## Branches

GET /api/branches

🔌 API Reference — Kitchen Analytics

Base URL: `https://api.kitchenanalytics.in` (production)
Local: `http://localhost:5000`

All endpoints require `Authorization: Bearer <token>` except `/api/health`, `/api/auth/signup`, `/api/auth/login`.

---

## Response Format

**Success (200/201):**
