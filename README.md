# Zibal Payment Gateway Proxy

A secure FastAPI microservice that acts as a proxy between Zibal payment gateway and your main application API. This service handles payment callbacks, verifies transactions, and forwards verified results to your backend with HMAC-SHA256 security signatures.

## 🌟 Features

- **Secure Payment Processing**: HMAC-SHA256 signed webhooks for authentication
- **Zibal Integration**: Handles callbacks and verifies payments with Zibal API
- **Referrer Fix**: Solves the "unauthorized domain" issue with Zibal
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Auto Redirects**: Automatically redirects users to success/failure pages
- **Health Checks**: Built-in health check endpoints for monitoring
- **Docker Ready**: Includes Dockerfile and docker-compose for easy deployment
- **API Documentation**: Interactive API docs with Scalar UI

## 📋 Prerequisites

- Python 3.11+
- Zibal merchant account
- Your main application API endpoint
- Frontend application for user redirects

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/payment-proxy.git
cd payment-proxy

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```env
# Zibal Configuration
ZIBAL_MERCHANT_ID=your_merchant_id
ZIBAL_VERIFY_URL=https://gateway.zibal.ir/v1/verify
ZIBAL_PAYMENT_URL=https://gateway.zibal.ir/start/

# Your Application URLs
Your_project_API_URL=https://your-api.example.com
Your_project_FRONTEND_URL=https://your-frontend.example.com

# Security (must match your main API)
WEBHOOK_SECRET=your_secure_random_secret_key

# Optional
DEBUG=false
```

### Running Locally

```bash
# Development mode
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The service will be available at `http://localhost:8000`

## 🐳 Docker Deployment

### Using Docker

```bash
# Build the image
docker build -t payment-proxy .

# Run the container
docker run -p 8000:8000 --env-file .env payment-proxy
```

### Using Docker Compose

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## 🏗️ Architecture

```
┌─────────┐      ┌──────────┐      ┌─────────────┐      ┌──────────────┐
│  User   │─────▶│ Frontend │─────▶│   Payment   │─────▶│    Zibal     │
└─────────┘      └──────────┘      │    Proxy    │      │   Gateway    │
     ▲                              └─────────────┘      └──────────────┘
     │                                     │                      │
     │                                     ▼                      │
     │                              ┌─────────────┐              │
     │                              │  Main API   │◀─────────────┘
     │                              └─────────────┘
     │                                     │
     └─────────────────────────────────────┘
```

### Payment Flow

1. **User initiates payment** on your frontend
2. **Frontend redirects** to `/redirect/{trackId}` on this proxy
3. **Proxy redirects** to Zibal gateway with correct referrer
4. **User completes payment** on Zibal
5. **Zibal sends callback** to `/api/zibal/callback`
6. **Proxy verifies** payment with Zibal API
7. **Proxy forwards** verified result to your main API via webhook
8. **Proxy redirects** user to success/failure page on your frontend

## 📡 API Endpoints

### `GET /`
Service information and status

### `GET /health`
Health check endpoint for monitoring systems

### `GET /docs`
Interactive API documentation (Scalar UI)

### `GET /redirect/{trackId}`
Redirect to Zibal payment gateway
- **Purpose**: Solves the "unauthorized domain" issue
- **Parameters**: 
  - `trackId`: Transaction ID from Zibal

### `GET /api/zibal/callback`
Receive payment callback from Zibal
- **Parameters**:
  - `trackId`: Transaction ID
  - `success`: Payment status (1=success, 0=failed)
  - `status`: Transaction status code
  - `orderId`: Order ID (optional)

## 🔒 Security

### HMAC Signature

All webhook requests to your main API are signed with HMAC-SHA256:

```python
signature = hmac.new(
    WEBHOOK_SECRET.encode(),
    f"{trackId}:{success}:{status}".encode(),
    hashlib.sha256
).hexdigest()
```

The signature is sent in the `X-Webhook-Signature` header.

### Verifying Webhooks in Your API

```python
import hmac
import hashlib

def verify_webhook(data, signature, secret):
    message = f"{data['trackId']}:{data['success']}:{data['status']}"
    expected = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

## 🔧 Configuration Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ZIBAL_MERCHANT_ID` | Your Zibal merchant ID | Yes | `zibal` |
| `ZIBAL_VERIFY_URL` | Zibal verification endpoint | No | `https://gateway.zibal.ir/v1/verify` |
| `ZIBAL_PAYMENT_URL` | Zibal payment gateway URL | No | `https://gateway.zibal.ir/start/` |
| `TICKETING_API_URL` | Your main API base URL | Yes | - |
| `TICKETING_FRONTEND_URL` | Your frontend base URL | Yes | - |
| `WEBHOOK_SECRET` | Shared secret for HMAC signatures | Yes | - |
| `DEBUG` | Enable debug mode | No | `false` |

## 🌐 Deployment

### Zibal Configuration

1. Log in to your Zibal merchant panel
2. Set the callback URL to: `https://your-domain.com/api/zibal/callback`
3. Add your domain to the allowed domains list

### Cloud Platforms

#### Liara (Iranian PaaS)

```bash
# Install Liara CLI
npm install -g @liara/cli

# Login
liara login

# Deploy
liara deploy
```

#### Heroku

```bash
# Create app
heroku create your-app-name

# Set environment variables
heroku config:set ZIBAL_MERCHANT_ID=your_merchant_id
heroku config:set TICKETING_API_URL=https://your-api.com
# ... set other variables

# Deploy
git push heroku main
```

#### AWS / GCP / Azure

Use the provided `Dockerfile` to deploy as a container service.

## 📊 Monitoring

### Health Checks

The service includes health check endpoints:
- `GET /health` - Returns `{"status": "healthy"}`
- Docker health check configured in Dockerfile

### Logging

All payment operations are logged with detailed information:
- Callback reception
- Zibal verification requests/responses
- Webhook forwarding
- User redirects
- Errors and exceptions

## 🧪 Testing

### Manual Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test service info
curl http://localhost:8000/
```

### Testing Payment Flow

1. Create a test payment in your main application
2. Get the `trackId` from Zibal
3. Navigate to `http://localhost:8000/redirect/{trackId}`
4. Complete the payment on Zibal (use test card if in sandbox mode)
5. Check logs to verify callback and webhook processing

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework for building APIs
- [Zibal](https://zibal.ir/) - Iranian payment gateway
- [Scalar](https://scalar.com/) - Beautiful API documentation

## 📞 Support

If you have any questions or issues, please open an issue on GitHub.

---

**Note**: This is a proxy service designed specifically for Zibal payment gateway. Make sure to configure your Zibal merchant account correctly and keep your `WEBHOOK_SECRET` secure.
