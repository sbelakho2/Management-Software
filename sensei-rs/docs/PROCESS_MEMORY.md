# Process Memory

The lifecycle that must be queryable end-to-end (item 99):

```
event → abnormality → problem → investigation → experiment → result → lesson → standard
```

The canonical `operational_events` envelope (migration 113) is the nervous system
(item 31-33): bitemporal (occurred_at vs recorded_at), many objects per event, source
references, sensitivity. Andon raises record events; the workflow engine (sensei-
workflow) checkpoints investigations; organizational memory stores the lesson chain.
