# EdHub360 Backend - AI Chat Services

A robust backend services platform providing AI-powered chat capabilities and microservices for the EdHub360 educational platform.

## Overview

The Backend repository contains modular microservices that power the AI chat and learning features of EdHub360. Built with Python and containerized with Docker, it provides scalable, production-ready APIs for the StudentHub frontend.

## Technology Stack

- **Primary Language**: Python (98%)
- **Containerization**: Docker (1.9%)
- **Templating**: Mako (0.1%)

## Features

### Core Services
- **AI Chat Services** - Intelligent chat functionality powered by AI
- **Authentication & Authorization** - Secure user authentication
- **Microservices Architecture** - Modular, scalable service design
- **RESTful APIs** - Clean, standardized API endpoints

### Key Capabilities
- Production-grade error handling
- Database integration and ORM support
- Authentication with JWT tokens
- Rate limiting and security features
- Comprehensive logging and monitoring
- Docker containerization for easy deployment

## Project Structure

```
Backend/
├── auth/              # Authentication microservice
├── chat/              # AI chat services
├── core/              # Shared utilities and core modules
├── migrations/        # Database migrations
├── tests/             # Test suites
├── Dockerfile         # Docker containerization
└── requirements.txt   # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.8+
- Docker & Docker Compose
- PostgreSQL (for persistence)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/edhub360/Backend.git
   cd Backend
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the development server**
   ```bash
   python -m uvicorn main:app --reload
   ```

### Docker Deployment

```bash
# Build the Docker image
docker build -t edhub360-backend .

# Run the container
docker run -p 8000:8000 --env-file .env edhub360-backend
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Configuration

Environment variables can be set in the `.env` file:

```
DATABASE_URL=postgresql://user:password@localhost/edhub360
JWT_SECRET_KEY=your-secret-key
AI_API_KEY=your-ai-service-key
CORS_ORIGINS=http://localhost:3000
```

## Testing

Run the test suite:

```bash
pytest tests/
pytest tests/ -v --cov=src  # With coverage
```

## Microservices

### Authentication Service
- User registration and login
- Google Sign-In integration
- JWT token management
- Password reset functionality

### Chat Service
- AI-powered conversation handling
- Message persistence
- Conversation history management
- Real-time updates support

### Additional Services
- User management
- Course integration
- Progress tracking
- Content serving

## Database

The backend uses PostgreSQL with Alembic for migration management.

**Key Tables**:
- `users` - User accounts
- `auth_credentials` - Authentication data
- `refresh_tokens` - Token management
- `conversations` - Chat history
- `messages` - Individual messages

## Performance & Scalability

- Asynchronous request handling with FastAPI
- Connection pooling for database
- Caching strategies for frequently accessed data
- Horizontal scaling support via containerization

## Security

- Password hashing with bcrypt
- JWT-based authentication
- Rate limiting on sensitive endpoints
- CORS configuration
- Input validation and sanitization
- Secure error handling (no sensitive data leakage)

## Logging & Monitoring

- Structured logging throughout the application
- Request/response logging
- Error tracking and reporting
- Performance metrics collection

## Contributing

1. Create a feature branch from `main`
2. Make your changes and write tests
3. Ensure all tests pass: `pytest tests/`
4. Submit a pull request

## CI/CD

The repository includes GitHub Actions workflows for:
- Automated testing on push and PRs
- Code quality checks
- Docker image building
- Deployment automation

## Deployment

Deployments are automated through GitHub Actions and can be deployed to:
- Cloud platforms (AWS, GCP, Azure)
- Kubernetes clusters
- Docker Compose environments
- Traditional VPS/server setups

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Review connection logs

### Authentication Failures
- Ensure JWT_SECRET_KEY is set correctly
- Check token expiration settings
- Verify Google OAuth credentials if using Sign-In

### AI Service Issues
- Validate AI_API_KEY configuration
- Check API rate limits
- Review service logs for details

## Related Repositories

- [StudentHub](https://github.com/edhub360/StudentHub) - Frontend UI repository

## License

[Your License Here]

## Support

For issues and questions:
1. Check existing GitHub issues
2. Create a new issue with detailed information
3. Contact the development team

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.
