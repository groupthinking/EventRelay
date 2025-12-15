"""
Cloud AI Provider Implementations

Individual implementations for each supported cloud AI provider.
"""

__all__ = []

# Conditional imports based on available dependencies
try:
    from .google_cloud import GoogleCloudAI
    __all__.append("GoogleCloudAI")
except ImportError:
    pass

try:
    from .aws_rekognition import AWSRekognition  
    __all__.append("AWSRekognition")
except ImportError:
    pass

try:
    from .azure_vision import AzureVision
    __all__.append("AzureVision") 
except ImportError:
    pass
