# Export policy for Lacuna
package lacuna.export

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# Default deny for exports - must explicitly allow
default allow := false

# Reasons for denial
deny[reason] if {
    # PROPRIETARY data cannot go to unmanaged locations
    input.source.classification == "PROPRIETARY"
    unmanaged_destination
    reason := "Cannot export PROPRIETARY data to unmanaged location"
}

deny[reason] if {
    # PROPRIETARY requires encryption for external destinations
    input.source.classification == "PROPRIETARY"
    external_destination
    not input.destination.encrypted
    reason := "PROPRIETARY data requires encryption for external destinations"
}

deny[reason] if {
    # INTERNAL cannot go external
    input.source.classification == "INTERNAL"
    external_destination
    reason := "INTERNAL data cannot be exported to external destinations"
}

# Allow if no deny rules match
allow if {
    count(deny) == 0
}

# Alternatives when denied
alternatives[alt] if {
    input.source.classification == "PROPRIETARY"
    unmanaged_destination
    pii_tags := [tag | some tag in input.source.tags; tag in ["PII", "PHI", "SSN", "EMAIL"]]
    alt := sprintf("Use anonymized version: lacuna.anonymize(data, %v)", [pii_tags])
}

alternatives[alt] if {
    input.source.classification == "PROPRIETARY"
    unmanaged_destination
    alt := "Save to governed location: /governed/workspace/"
}

alternatives[alt] if {
    input.source.classification == "PROPRIETARY"
    unmanaged_destination
    alt := "Request exception: lacuna.request_exception()"
}

# Helper rules
unmanaged_destination if {
    unmanaged_patterns := ["~/Downloads", "/tmp", "Downloads", "Desktop"]
    some pattern in unmanaged_patterns
    contains(input.destination.path, pattern)
}

external_destination if {
    external_patterns := ["s3://", "gs://", "azure://", "http://", "https://"]
    some pattern in external_patterns
    startswith(input.destination.path, pattern)
}

