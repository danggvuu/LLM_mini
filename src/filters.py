from typing import List, Optional
from pydantic import BaseModel, model_validator
from qdrant_client.http import models as qmodels

class MetadataFilter(BaseModel):
    notebook_id: Optional[str] = None
    filename: Optional[str] = None
    filenames: Optional[List[str]] = None
    page: Optional[int] = None
    section: Optional[str] = None
    document_id: Optional[str] = None
    
    @model_validator(mode="after")
    def _normalize(self) -> "MetadataFilter":
        names = [n.strip() for n in (self.filenames or []) if isinstance(n, str) and n.strip()]
        if not names:
            self.filenames = None
        elif len(names) == 1:
            self.filename, self.filenames = names[0], None
        else:
            # Multi-file query clears single filename and page to avoid confusion
            self.filename, self.filenames, self.page = None, names, None
            
        if self.filename is not None:
            self.filename = self.filename.strip() or None
        if self.section is not None:
            self.section = self.section.strip() or None
        if self.document_id is not None:
            self.document_id = self.document_id.strip() or None
            
        return self

def _coerce_filter(filters):
    if filters is None:
        return None
    if isinstance(filters, dict):
        return MetadataFilter(**filters)
    if isinstance(filters, MetadataFilter):
        return filters
    return None

def filters_to_dict(filters):
    f = _coerce_filter(filters)
    return None if f is None else f.model_dump(exclude_none=True) or None

def filters_to_qdrant(filters):
    flat = filters_to_dict(filters)
    if not flat:
        return None
        
    conditions = []
    for field, value in flat.items():
        if field == "filenames" and isinstance(value, list):
            conditions.append(qmodels.FieldCondition(
                key="metadata.filename", match=qmodels.MatchAny(any=value)
            ))
        elif isinstance(value, (str, int)):
            conditions.append(qmodels.FieldCondition(
                key=f"metadata.{field}", match=qmodels.MatchValue(value=value)
            ))
            
    return qmodels.Filter(must=conditions) if conditions else None
