---
name: sql-safety
description: Verify safe student SQL execution and controlled PostgreSQL DDL in the HotelDB lecture.
---

# Database Safety

- Student requests use `hotel_student` only; `GRANT SELECT` is the primary security barrier.
- The app also requires a single SELECT statement, `SET TRANSACTION READ ONLY`, a timeout, limited rows and a server-side cursor.
- Never permit user-provided arbitrary identifiers in SQL format strings.
- Never execute a migration or seed reset as part of a student request.
- For `CREATE INDEX CONCURRENTLY`, use a separate teacher-approved owner connection outside a transaction.
- Verify a `Seq Scan` / `Index Scan` from a **real** `EXPLAIN (ANALYZE, BUFFERS)`, not from an assumed speedup.
- Performance of remote HTTP requests includes network latency. Use DB execution times for comparisons.
- Never grant student role `CREATE`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `EXECUTE` on custom mutating functions, or predefined admin roles.
- Testing true permission isolation requires a running PostgreSQL instance; unit tests alone are insufficient.
