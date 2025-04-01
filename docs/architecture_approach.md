# Architecture Approach: Hexagonal (Ports & Adapters)

This document details the Hexagonal Architecture (also known as Ports and Adapters) approach adopted for the VirtualStack backend project.

## Core Principles

The primary goal of this architecture is to isolate the core application logic (the "domain") from external concerns such as UI frameworks, databases, third-party APIs, and system infrastructure. This promotes:

1.  **Testability:** The core domain logic can be tested in isolation without external dependencies.
2.  **Maintainability:** Changes in external technologies (e.g., switching database vendors) have minimal impact on the core logic.
3.  **Flexibility:** New adapters can be added to support different delivery mechanisms (e.g., REST API, gRPC, CLI) or infrastructure integrations without modifying the core.
4.  **Technology Agnosticism:** The core domain logic is independent of specific frameworks or tools used in the adapters.

## Key Components

### 1. The Hexagon (Core Domain)

*   **Location:** Primarily within `src/virtualstack/models/` (domain entities), `src/virtualstack/schemas/` (data transfer objects, some representing core concepts), and `src/virtualstack/services/` (application/domain services encapsulating business logic).
*   **Responsibility:** Contains the essential business rules, entities, value objects, and application logic of VirtualStack. This includes concepts like `User`, `Tenant`, `Role`, `Permission`, and the rules governing their interactions (e.g., how roles are assigned, how permissions are checked).
*   **Key Characteristic:** **Must not depend on any adapter code.** It defines its own needs through Ports (interfaces).

### 2. Ports

*   **Concept:** Interfaces defined *by the core domain* that dictate how external components can interact with it (driving ports) or how the core domain interacts with external services it needs (driven ports).
*   **Implementation:**
    *   **Driving Ports:** Often implicitly defined by the public methods of the core application services (`src/virtualstack/services/`). The API endpoints act as adapters calling these service methods.
    *   **Driven Ports:** Less explicit in our current Python implementation but conceptually represent interfaces for things the core *needs*, like data persistence. The `CRUDBase` in `src/virtualstack/services/base.py` acts as a form of abstract interface for common persistence operations. More complex interactions (like interacting with vCenter) would ideally have explicit Port interfaces defined in the core.

### 3. Adapters

*   **Location:**
    *   **Primary/Driving Adapters:** `src/virtualstack/api/` (FastAPI endpoints translating HTTP requests into calls to core service methods).
    *   **Secondary/Driven Adapters:** `src/virtualstack/db/` (SQLAlchemy implementation for database interactions, fulfilling the persistence needs of the core), `src/virtualstack/adapters/` (intended location for external system adapters like vCenter).
*   **Responsibility:** Implement the Ports to bridge the gap between the core domain and the outside world.
    *   Primary adapters drive the application (e.g., handling HTTP requests).
    *   Secondary adapters are driven by the application (e.g., storing data in a specific database, calling an external API).

## Specific Design Decisions

### IAM Module (Roles & Permissions)

*   **Global Role Definitions:** The `Role` model itself (`src/virtualstack/models/iam/role.py`) represents a global definition of a role. Permissions are associated via the `role_permissions` association table (`src/virtualstack/models/iam/role_permissions.py`). This allows for standard, predefined roles (e.g., "Tenant Admin", "Read Only User").
*   **Tenant-Specific Role Assignment:** The assignment of global roles to users happens within the context of a specific `Tenant`. This is managed through the `user_tenant_roles` association table (`src/virtualstack/models/iam/user_tenant_role.py`) linking `User`, `Role`, and `Tenant`.
*   **Permission Checks:** The `require_permission` dependency (`src/virtualstack/api/deps.py`) acts as part of a primary adapter mechanism, checking if the authenticated user possesses the necessary permission (derived from their assigned roles within the tenant specified in the request context, often via the `X-Tenant-ID` header) before allowing access to an endpoint. This dependency needs further refinement, particularly around handling different permission scopes (global vs. tenant) and ensuring correct context propagation.

### API Key Handling

*   **Timezone Management:** All timestamp fields (`created_at`, `updated_at`, `expires_at`, `last_used_at`) in the `APIKey` model (`src/virtualstack/models/iam/api_key.py`) are defined using `DateTime(timezone=True)` to ensure timezone awareness and consistency. The application logic (e.g., in `api_key_service`) correctly handles timezone-aware `datetime` objects (using `datetime.now(timezone.utc)` or `.replace(tzinfo=timezone.utc)` where necessary) for comparisons and updates.
*   **Expiry Validation:** The `validate_api_key` service method performs timezone-aware comparison between the key's `expires_at` and the current UTC time.
*   **Known Issue (`created_at`):** Despite the timezone fixes, there is a persistent issue where `created_at` appears as `None` during Pydantic serialization in list endpoints (`GET /api/v1/api-keys/`). This suggests a potential issue with SQLAlchemy session state or object loading for `server_default` values when retrieving multiple existing records.

### Tenant Isolation

*   **Core Principle:** Data and operations must be strictly isolated between tenants, except for superuser access.
*   **Implementation:**
    *   **Middleware/Context:** The `X-Tenant-ID` header is commonly used in requests to establish the tenant context. Dependencies like `require_permission` use this context.
    *   **Service Layer:** Core service methods (`src/virtualstack/services/`) are responsible for using the `tenant_id` (passed down from the API layer/dependency injection) to filter database queries and validate operations, ensuring that actions only affect resources belonging to the correct tenant. This is critical for all CRUD operations on tenant-scoped resources and associations (like `UserTenantRole`).
    *   **Database Schema:** Foreign keys linking resources back to a `tenant_id` are essential. Association tables for roles (`user_tenant_roles`) must also include the `tenant_id`.

## Development Flow

Adhering to the Hexagonal Architecture, the development prioritizes:

1.  Defining and implementing the core domain logic and entities.
2.  Defining the necessary ports (interfaces) for interaction.
3.  Implementing primary adapters (like the API) to drive the core.
4.  Implementing secondary adapters (like database persistence) driven by the core.
5.  Ensuring robust testing at each layer, especially isolating core logic tests.

This approach ensures the most critical business logic is stable and well-defined before integrating with external systems or specific technologies. 