# ADR-0002: Relationship Calculation Algorithm

## Status
Accepted

## Context
The family tree application needs to calculate complex relationships between any two people in a family tree (e.g., "second cousin", "great aunt", "step-brother"). The current `Person` model only stores direct parent relationships but doesn't provide a way to calculate extended family relationships.

## Decision
Implement a recursive relationship calculation algorithm that:

1. Uses graph traversal to find the shortest path between two people
2. Analyzes the path to determine the relationship type
3. Handles special cases like adoption, step-relationships, and multiple marriages
4. Caches frequently calculated relationships for performance

## Technical Implementation
- Create `RelationshipCalculator` service class
- Add relationship caching to reduce computation overhead
- Support both biological and legal relationships
- Provide relationship description in multiple languages

## Consequences
**Positive:**
- Enables automatic relationship discovery and display
- Supports complex family structures
- Improves user experience with relationship insights
- Scalable approach for large family trees

**Negative:**
- Adds computational complexity
- Requires careful handling of edge cases
- May need performance optimization for very large trees

## Alternatives Considered
- Pre-calculated relationship tables (too rigid)
- Simple parent-child only relationships (insufficient)
- Third-party genealogy libraries (vendor lock-in)