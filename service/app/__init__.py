"""EventRelay clean-spine service.

A single linear pipeline service grown against the success criteria in
docs/PORTING_PARAMETERS.md. This package deliberately shares no code with the
legacy src/ tree; nothing is imported from it until it is traced to a success
criterion and ported explicitly.
"""
