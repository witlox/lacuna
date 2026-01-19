# Base Rego policy for Lacuna classification
package lacuna.classification

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# Default: allow operations
default allow := true

# Default classification is PUBLIC
default tier := "PUBLIC"

# Classification result structure
classification[result] if {
    result := {
        "tier": tier,
        "confidence": confidence,
        "reasoning": reasoning,
    }
}

# PROPRIETARY classification rules
tier := "PROPRIETARY" if {
    proprietary_match
}

proprietary_match if {
    # Check for customer references
    contains(lower(input.query), "customer")
}

proprietary_match if {
    # Check for project context
    input.context.project != "learning"
    input.context.project != "public"
    input.context.project != null
}

proprietary_match if {
    # Check for PII tags
    some tag in input.tags
    tag in ["PII", "PHI", "SSN", "CREDIT_CARD"]
}

# INTERNAL classification rules
tier := "INTERNAL" if {
    not proprietary_match
    internal_match
}

internal_match if {
    internal_terms := ["deployment", "infrastructure", "monitoring", "staging"]
    some term in internal_terms
    contains(lower(input.query), term)
}

# Confidence based on match type
confidence := 1.0 if proprietary_match
confidence := 0.9 if internal_match
confidence := 0.8 if not proprietary_match
confidence := 0.8 if not internal_match

# Reasoning
reasoning := "Query references customer data" if {
    contains(lower(input.query), "customer")
}

reasoning := "Project context indicates proprietary" if {
    input.context.project != null
    input.context.project != "learning"
    input.context.project != "public"
}

reasoning := "Contains PII indicators" if {
    some tag in input.tags
    tag in ["PII", "PHI", "SSN"]
}

reasoning := "Internal infrastructure reference" if internal_match

reasoning := "No sensitive patterns detected" if {
    not proprietary_match
    not internal_match
}

