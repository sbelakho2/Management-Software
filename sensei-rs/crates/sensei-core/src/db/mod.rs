//! Database handles: the typed tenant transaction is the ONLY way
//! tenant-domain code touches RLS-protected tables.

pub mod tenant_tx;
