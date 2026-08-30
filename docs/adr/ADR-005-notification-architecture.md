# ADR-005: Notification Architecture

## Status

Accepted

## Context

The academy management system requires a centralized notification system that can deliver messages through multiple channels (SMS, Telegram, Bale, Email, in-app) while maintaining loose coupling with existing modules and allowing future extensibility.

Key requirements:
- Multi-channel delivery with independent tracking
- Provider abstraction for channel-specific implementations
- Graceful degradation when provider credentials are missing
- Event-driven integration with existing P1-P8 modules
- User preferences for notification types and channels
- Mandatory notifications that bypass preferences
- Persian RTL UI for admin and user interfaces

## Decision

### Architecture Pattern

**Provider Abstraction with Registry Pattern**

The notification system uses:
1. **Provider Abstraction**: Abstract base class `NotificationProvider` defines the interface for all notification channels
2. **Provider Registry**: Central registry maps channels to their implementations
3. **Independent Delivery Records**: Each channel delivery is tracked separately via `NotificationDelivery`
4. **Event-Driven Integration**: Existing services emit events that trigger notifications
5. **Preference System**: Users can enable/disable notification types per channel (except mandatory)

### Key Design Choices

1. **Infrastructure Isolation**: All provider-specific code (HTTP clients, API integrations) stays in `app/infrastructure/notification/`
2. **Domain Independence**: Domain layer contains only entities and enums, no infrastructure dependencies
3. **Graceful Degradation**: Missing provider credentials result in `NullProvider` that silently fails
4. **Mandatory Notifications**: System-critical notifications (WELCOME, PASSWORD_CHANGED) ignore user preferences
5. **In-App Notifications**: Internal notifications don't require external provider configuration

### Database Design

- `notifications`: Core notification records with type, priority, status
- `notification_deliveries`: Independent per-channel delivery tracking
- `notification_templates`: Reusable message templates with variable rendering
- `notification_preferences`: Per-user, per-type, per-channel settings
- `in_app_notifications`: Internal notification records with read status

### Provider Implementation

Each provider implements:
- `send(notification, recipient)`: Deliver notification to recipient
- `validate_recipient(recipient)`: Validate recipient format
- `is_available()`: Check if provider is properly configured

Providers:
- **SMS**: Generic HTTP API (environment-configured endpoint)
- **Telegram**: Bot API with token-based authentication
- **Bale**: Bot API (similar to Telegram)
- **Email**: SMTP with TLS support
- **In-App**: Direct database insertion (no external calls)

## Consequences

### Positive

- **Loose Coupling**: Existing modules don't depend on notification infrastructure
- **Extensibility**: New channels can be added by implementing `NotificationProvider`
- **Reliability**: Missing credentials don't break application startup
- **Flexibility**: Users control their notification preferences
- **Auditability**: Each delivery attempt is tracked independently

### Negative

- **Complexity**: Multi-channel tracking adds database complexity
- **Event Management**: Must carefully manage which events trigger notifications
- **Preference Sync**: User preference changes may take time to propagate

### Mitigations

- **Graceful Degradation**: NullProvider handles missing credentials silently
- **Preference Caching**: Consider caching preferences for performance
- **Event Batching**: Batch high-frequency events to prevent notification overload

## Alternatives Considered

### 1. Direct Provider Calls in Services

**Rejected**: Would create tight coupling between business logic and notification infrastructure.

### 2. Message Queue (Celery/RabbitMQ)

**Rejected**: Adds operational complexity for a system that doesn't require real-time delivery guarantees.

### 3. Third-Party Notification Service (OneSignal, etc.)

**Rejected**: Introduces external dependency and potential vendor lock-in.

## Implementation Notes

- Provider-specific HTTP clients use `requests` library (already in project dependencies)
- Environment variables for provider credentials follow `NOTIFICATION_*` pattern
- All provider methods return `ProviderResult` for consistent error handling
- Event handlers are registered during application factory initialization

---

**Decision Date**: 2026-08-30
**Decided By**: AI Agent (following established project architecture)
**Review Date**: When approaching v1 stability
