#!/bin/bash

echo "🚀 Cloud Kitchen Setup Script"
echo "=============================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python
echo -e "\n${BLUE}Checking Python...${NC}"
if ! command -v python &> /dev/null; then
    echo -e "${RED}Python not found. Please install Python 3.9+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python found: $(python --version)${NC}"

# Check Node
echo -e "\n${BLUE}Checking Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js not found. Please install Node.js 16+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js found: $(node --version)${NC}"

# Backend Setup
echo -e "\n${BLUE}Setting up Backend...${NC}"
cd backend
python -m venv venv
source venv/bin/activate 2>/dev/null || venv\Scripts\activate
pip install -r requirements.txt
echo -e "${GREEN}✓ Backend dependencies installed${NC}"

# Frontend Setup
echo -e "\n${BLUE}Setting up Frontend...${NC}"
cd ../frontend
npm install
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# Create .env if not exists
echo -e "\n${BLUE}Checking configuration...${NC}"
if [ ! -f ../backend/.env ]; then
    echo "MONGO_URI=mongodb://localhost:27017/" > ../backend/.env
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

echo -e "\n${GREEN}=============================="
echo "✨ Setup Complete!${NC}"
echo -e "${GREEN}=============================="
echo ""
echo "📝 Next steps:"
echo "1. Start MongoDB: mongod"
echo "2. Train ML model: python setup_ml.py"
echo "3. Start backend: cd backend && python -m uvicorn app.main:app --reload"
echo "4. Start frontend: cd frontend && npm run dev"
echo ""
