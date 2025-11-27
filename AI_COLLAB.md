# AI Collaboration Guidelines for paku-iot

This document provides guidelines for AI-assisted development on the paku-iot project.

## Security & Secrets Handling

### Critical Rules

1. **Never commit secrets to version control**
   - No passwords, API keys, tokens, or credentials in code
   - No secrets in commit messages or PR descriptions
   - No secrets in issue comments or chat history

2. **Use environment variables for all secrets**
   - All sensitive configuration must be in `compose/.env` (git-ignored)
   - Use `compose/.env.example` as a template showing required variables
   - Default values in code should be safe placeholders only

3. **Environment File Management**
   - `compose/.env` is git-ignored and contains actual secrets
   - `compose/.env.example` is committed and documents required variables
   - To set up locally: `cp compose/.env.example compose/.env` then edit `compose/.env`

### Required Environment Variables

The stack requires the following environment variables (see `compose/.env.example`):

```bash
# Database
POSTGRES_USER=paku
POSTGRES_PASSWORD=paku          # Change in production!
POSTGRES_DB=paku

# MQTT Broker
MQTT_HOST=mosquitto
MQTT_PORT=1883

# Grafana
GF_SECURITY_ADMIN_PASSWORD=admin  # Change in production!
```

### Production Deployment

Before deploying to production:
- Generate strong, unique passwords for all services
- Use environment-specific `compose/.env` files (never commit them)
- Consider using secrets management tools (e.g., Docker secrets, vault)
- Enable authentication and TLS for MQTT broker
- Use HTTPS for Grafana and any web interfaces

## Development Workflow

### Setting Up Local Environment

1. Clone the repository
2. Copy environment template: `cp compose/.env.example compose/.env`
3. Edit `.env` with your local configuration
4. Start the stack: `docker compose -f compose/stack.yaml up --build`

### Making Changes

1. Keep changes minimal and focused
2. Test locally before committing
3. Document environment variable changes in `compose/.env.example`
4. Update README.md if user-facing setup changes

### Adding New Services

When adding new services that require configuration:

1. Add environment variables to `compose/stack.yaml` with defaults:
   ```yaml
   environment:
     - MY_VAR=${MY_VAR:-default_value}
   ```

2. Document the variable in `compose/.env.example`:
   ```bash
   # Description of what this variable does
   MY_VAR=default_value
   ```

3. Update documentation in README.md if needed

## Future Work

### MQTT Security (not in current sprint)

The MQTT broker currently runs without authentication for local development simplicity. Future hardening should include:

- Username/password authentication
- TLS encryption
- Access control lists (ACLs) per topic
- Certificate-based authentication for devices

This is documented as future work and should not be implemented in the current phase.

### Multi-Environment Support

Future considerations:
- Separate dev/staging/prod compose configurations
- Environment-specific secrets management
- Remote deployment to cloud VMs

## Testing

### Manual Testing Checklist

After environment variable changes:
- [ ] Stack starts successfully: `docker compose -f compose/stack.yaml up`
- [ ] All services are healthy: `docker compose ps`
- [ ] Services can communicate (MQTT → Collector → Postgres)
- [ ] Grafana accessible at http://localhost:3000
- [ ] PostgreSQL accessible at localhost:5432
- [ ] Default credentials work as documented

### Configuration Validation

```bash
# Validate compose file
docker compose -f compose/stack.yaml config

# Check environment variable resolution
docker compose -f compose/stack.yaml config | grep -A 5 "environment:"
```

## Common Issues

### "Permission denied" errors
- Ensure Docker daemon is running
- Check file permissions on volumes
- On Linux, may need to add user to docker group

### Services can't connect
- Verify all environment variables are set correctly
- Check service names match between compose file and env vars
- Review docker network with `docker network inspect compose_default`

### .env file ignored by git
- This is intentional! Use `compose/.env.example` as reference
- Never commit `.env` to version control
- To force-add (not recommended): `git add -f .env`

## Documentation

- [Requirements](docs/requirements.md) — Project requirements and scope
- [MQTT Schema](docs/mqtt_schema.md) — Message format and topics
- [README](README.md) — Quick start and setup guide

## Contact

For questions or issues with the project, please open a GitHub issue.
