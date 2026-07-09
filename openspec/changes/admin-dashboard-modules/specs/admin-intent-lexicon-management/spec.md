## ADDED Requirements

### Requirement: Admin can view intent taxonomy
The system SHALL provide an admin API to view the current intent taxonomy including space types, points, styles, materials, and aliases.

#### Scenario: View taxonomy
- **WHEN** admin requests /api/admin/intent-taxonomy
- **THEN** the system SHALL return the full taxonomy loaded from `intent_taxonomy.yaml`

### Requirement: Admin can view alias proposals
The system SHALL provide an admin API to view alias expansion proposals generated from user corrections.

#### Scenario: List proposals
- **WHEN** admin requests /api/admin/intent-taxonomy/alias-proposals
- **THEN** the system SHALL return proposals grouped by field with occurrence count and confidence

### Requirement: Admin can apply alias proposals
The system SHALL allow admin to apply selected alias proposals to the taxonomy YAML file.

#### Scenario: Apply proposal
- **WHEN** admin approves proposal to add alias "商厦中庭" for space_type "购物中心中庭"
- **THEN** the system SHALL append the alias to `intent_taxonomy.yaml` and reload the taxonomy

### Requirement: Admin can manually add aliases
The system SHALL allow admin to manually add an alias to a taxonomy entry.

#### Scenario: Manual alias
- **WHEN** admin adds alias "中庭吊饰" to point "中庭"
- **THEN** the system SHALL update `intent_taxonomy.yaml` and reflect the change in subsequent intent recognition calls
