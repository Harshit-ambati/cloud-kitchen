# Cloud Kitchen Management System

A full-stack delivery optimization platform using machine learning for ETA prediction and intelligent route optimization.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                  │
│              Real-time map & order management              │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼────────────────────────────────────┐
│                  Backend (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Orders API   │  │ Agents API   │  │ Optimizer    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼─────┐   ┌─────▼──────┐   ┌────▼─────┐
   │ MongoDB   │   │ ML Models  │   │ OR-Tools  │
   └──────────┘   └────────────┘   └──────────┘
```

## 🚀 Features

- ✅ **Real-time Order Management** - Create, track, and manage delivery orders
- ✅ **ML-based ETA Prediction** - Predict delivery time using Random Forest
- ✅ **Route Optimization** - Assign orders to agents optimally using OR-Tools
- ✅ **Live Tracking Map** - OpenStreetMap with real-time agent & order locations
- ✅ **Agent Management** - Create and manage delivery partners
- ✅ **Order Status Tracking** - From placed → accepted → in_transit → delivered

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+
- MongoDB (local or Atlas)

## ⚙️ Setup Instructions

### 1. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure MongoDB

Edit `backend/.env`:
```
MONGO_URI=mongodb://localhost:27017/
```

For MongoDB Atlas:
```
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

### 3. Train ML Model

```bash
python setup_ml.py
```

This will:
- Generate 5000 synthetic training samples
- Train the RandomForest ETA prediction model
- Save the model to `ml/model.pkl`

### 4. Start Backend Server

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Server runs at: `http://localhost:8000`

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

## 📡 API Endpoints

### Orders
```
POST   /api/orders/create              - Create new order
GET    /api/orders/                    - Get all orders
GET    /api/orders/{order_id}          - Get specific order
PUT    /api/orders/{order_id}/status   - Update order status
GET    /api/orders/agent/{agent_id}    - Get agent's orders
POST   /api/orders/optimize-assignments - Optimize order assignments
```

### Agents
```
POST   /api/agents/create              - Register new agent
GET    /api/agents/                    - Get all agents
GET    /api/agents/{agent_id}          - Get specific agent
PUT    /api/agents/{agent_id}          - Update agent location/availability
DELETE /api/agents/{agent_id}          - Delete agent
```

## 📊 ML Models

### ETA Prediction Model

**Features:**
- `distance_km` - Distance between kitchen and user
- `hour` - Hour of day (0-23)
- `traffic` - Traffic multiplier (1-4)

**Model:** Random Forest Regressor
**Accuracy:** Trained on 5000 synthetic samples

### Route Optimization

Uses Google OR-Tools Vehicle Routing Problem solver to:
- Minimize total travel distance
- Balance workload among agents
- Respect agent availability

## 🧪 Testing

### Test Order Creation

```bash
curl -X POST http://localhost:8000/api/orders/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_lat": 28.6292,
    "user_lng": 77.2197,
    "kitchen_lat": 28.6139,
    "kitchen_lng": 77.209,
    "order_type": "regular"
  }'
```

### Test Agent Creation

```bash
curl -X POST http://localhost:8000/api/agents/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Raj Kumar",
    "lat": 28.6139,
    "lng": 77.209
  }'
```

## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── db.py
│   │   ├── routes/
│   │   │   ├── orders.py
│   │   │   └── agents.py
│   │   └── services/
│   │       ├── distance.py
│   │       └── optimizer.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── OrderForm.jsx
│   │   │   ├── OrderList.jsx
│   │   │   ├── AgentForm.jsx
│   │   │   └── AgentList.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── ml/
│   ├── training/
│   │   └── generate_data.py
│   ├── eta_model.py
│   ├── predict_eta.py
│   └── route_optimizer.py
└── setup_ml.py
```

## 🔧 Troubleshooting

**MongoDB Connection Error:**
- Ensure MongoDB is running locally or update connection string in `.env`

**Module Not Found:**
```bash
# Reinstall dependencies
pip install -r requirements.txt
npm install
```

**Port Already in Use:**
```bash
# Change port in backend
uvicorn app.main:app --port 8001
```

## 🎯 Next Steps

- [ ] Add real-time WebSocket updates
- [ ] Implement user authentication
- [ ] Add payment integration
- [ ] Create mobile app
- [ ] Deploy to production
- [ ] Add delivery feedback/ratings
- [ ] Implement surge pricing

## 📝 License

MIT License
