# EOS DBP — Production Deployment Plan (Final)
## Date: 2026-08-28
## Status: APPROVED — Ready for Execution

---

## Hetzner Pricing (2026)

```
⚠️ Prices increased June 15, 2026:
   CX/CAX: +30-40%
   CPX/CCX: more than doubled

Recommended Options (Germany/Finland — cheapest):
├── CPX31:  4 vCPU, 8GB RAM,  160GB NVMe  ~€29/mo (~$31)
├── CPX41:  8 vCPU, 16GB RAM, 240GB NVMe  ~€33/mo (~$36)
└── CPX21:  3 vCPU, 4GB RAM,  80GB NVMe   ~€17/mo (~$19)
```

### Recommendation

```
START with CPX31 (€29/mo):
├── 4 vCPU (sufficient for 1-10 tenants)
├── 8GB RAM (PostgreSQL + FastAPI + Nginx)
├── 160GB NVMe (fast I/O for database)
├── 20TB traffic included
└── Upgrade to CPX41 when needed
```

---

## Deployment Phases (12 Steps)

```
[1]  Backup + Release Package     ← Dev copy frozen
[2]  VPS Provisioning             ← Hetzner CPX31
[3]  Server Hardening             ← Security first
[4]  Production Configuration     ← .env, secrets
[5]  Database Migration/Restore   ← PostgreSQL 18
[6]  Docker Deployment            ← Containerized
[7]  Nginx + SSL + Domain         ← HTTPS ready
[8]  Production Smoke Test        ← Verify before customers
[9]  First Tenant                 ← Real company setup
[10] Real Business Test           ← Live transactions
[11] Go-Live                      ← Public access
[12] Post-Go-Live Monitoring      ← 24/7 watch
```

---

## CRITICAL CONSTRAINTS

```
🔒 D:\EOS\Eos final → NEVER MODIFIED (Master/Recovery Copy)
🔒 PostgreSQL version must match (18.x)
🔒 Every phase has verification gate
🔒 No assumption of success without testing
🔒 Backup verified before go-live
```

---

## Detailed Plan

### PHASE 1: Backup + Release Package

```
Actions:
├── Create EOS-Release-1.0/ directory
├── Copy application code
├── Export database (pg_dump)
├── Generate .env.production template
└── Create checksums

Verification:
├── [ ] Release package complete
├── [ ] Database backup restorable
├── [ ] Dev copy untouched (D:\EOS\Eos final)
└── [ ] Checksums match
```

### PHASE 2: VPS Provisioning

```
Actions:
├── Create Hetzner account
├── Deploy CPX31 (Germany)
├── Create SSH key pair
├── Generate root password
└── Note server IP

Verification:
├── [ ] SSH access works
├── [ ] Ubuntu 22.04 installed
├── [ ] System updated
└── [ ] Network accessible
```

### PHASE 3: Server Hardening

```
Actions:
├── Create 'eos' user
├── Configure SSH key-only auth
├── Disable root login
├── Configure UFW firewall
│   ├── Allow 22 (SSH)
│   ├── Allow 80 (HTTP)
│   ├── Allow 443 (HTTPS)
│   └── Deny all else
├── Install fail2ban
├── Set timezone (UTC or target region)
└── Configure auto-updates

Verification:
├── [ ] SSH key auth works
├── [ ] Root login disabled
├── [ ] Firewall active
├── [ ] fail2ban running
└── [ ] No unauthorized access
```

### PHASE 4: Production Configuration

```
Actions:
├── Install Docker + Docker Compose
├── Install PostgreSQL 18
├── Create .env.production
│   ├── DATABASE_URL
│   ├── SECRET_KEY (random 64 chars)
│   ├── ENCRYPTION_KEY (random 64 chars)
│   ├── CORS_ORIGINS
│   └── ALLOWED_HOSTS
├── Set secure database password
└── Configure backup directory

Verification:
├── [ ] Docker running
├── [ ] PostgreSQL running
├── [ ] .env loaded correctly
├── [ ] Secrets generated
└── [ ] Database accessible
```

### PHASE 5: Database Migration/Restore

```
Actions:
├── Create database eos_main
├── Create user eos with password
├── Restore from backup
│   └── psql < eos_backup.sql
├── Verify table count (394)
├── Run any pending migrations
└── Create admin user

Verification:
├── [ ] Table count = 394
├── [ ] Index count = 1155
├── [ ] Tenant data present
├── [ ] Admin user login works
└── [ ] No migration errors
```

### PHASE 6: Docker Deployment

```
Actions:
├── Build Docker image
├── Start containers (db, api, nginx)
├── Verify health endpoint
├── Check logs for errors
└── Test API responds

Verification:
├── [ ] All containers running
├── [ ] Health check returns 200
├── [ ] No errors in logs
├── [ ] API responds to /api/version
└── [ ] Database connection OK
```

### PHASE 7: Nginx + SSL + Domain

```
Actions:
├── Configure Nginx
├── Point DNS to VPS IP
│   ├── app.yourdomain.com → VPS
│   └── api.yourdomain.com → VPS
├── Install Certbot
├── Obtain SSL certificate
├── Configure auto-renewal
└── Test HTTPS access

Verification:
├── [ ] HTTP → HTTPS redirect works
├── [ ] SSL certificate valid
├── [ ] No mixed content warnings
├── [ ] Auto-renewal configured
└── [ ] Accessible from internet
```

### PHASE 8: Production Smoke Test

```
Actions:
├── Login works
├── Create test item
├── Create test customer
├── Create test order
├── Generate test invoice
├── View reports
├── Test all core endpoints
└── Delete test data

Verification:
├── [ ] Login: 200 OK
├── [ ] Items CRUD: 200 OK
├── [ ] Customers CRUD: 200 OK
├── [ ] Orders: 200 OK
├── [ ] Invoices: 200 OK
├── [ ] Reports: 200 OK
├── [ ] Performance < 1s
└── [ ] No errors in logs
```

### PHASE 9: First Tenant

```
Actions:
├── Create real company
├── Setup admin user + roles
├── Configure chart of accounts
├── Setup warehouses
├── Add opening balances
├── Add products
├── Add customers/suppliers
└── Configure industry module

Verification:
├── [ ] Company created
├── [ ] Admin user works
├── [ ] Chart of accounts loaded
├── [ ] Warehouses configured
├── [ ] Opening balances entered
├── [ ] Products added
├── [ ] Customers/suppliers added
└── [ ] Industry module active
```

### PHASE 10: Real Business Test

```
Actions:
├── Create real transaction
├── Generate real invoice
├── Process payment
├── Generate report
├── Test bank reconciliation
├── Test customer portal
└── Test multi-currency

Verification:
├── [ ] Transaction recorded
├── [ ] Invoice generated correctly
├── [ ] Payment processed
├── [ ] Report accurate
├── [ ] Bank reconciliation works
├── [ ] Portal accessible
└── [ ] Multi-currency works
```

### PHASE 11: Go-Live

```
Actions:
├── Final backup verified
├── Monitoring active
├── Backup cron running
├── Domain accessible
├── SSL working
├── All systems operational
└── Provide access to customer

Verification:
├── [ ] Backup verified
├── [ ] Monitoring active
├── [ ] Backup cron verified
├── [ ] Domain accessible
├── [ ] SSL working
├── [ ] All systems green
└── [ ] Customer has access
```

### PHASE 12: Post-Go-Live Monitoring

```
Actions:
├── Monitor 24 hours
├── Check backup daily
├── Review error logs
├── Check performance
├── Gather user feedback
└── Plan improvements

Verification:
├── [ ] 24 hours uptime
├── [ ] Backup verified daily
├── [ ] No critical errors
├── [ ] Performance stable
├── [ ] User feedback collected
└── [ ] Improvement plan created
```

---

## Cost Summary

```
Monthly Costs:
├── Hetzner CPX31:           €29/mo (~$31)
├── Domain:                  ~$1/mo ($12/year)
├── SSL (Let's Encrypt):     Free
├── Monitoring:              Free
├── Backup storage:          Free (on VPS)
└── Total:                   ~$32/month

First Year: ~$396
```

---

## Timeline

```
Day 1: Phases 1-3 (Backup, VPS, Hardening)
Day 2: Phases 4-5 (Config, Database)
Day 3: Phases 6-7 (Docker, SSL)
Day 4: Phases 8-9 (Smoke Test, First Tenant)
Day 5: Phases 10-12 (Business Test, Go-Live, Monitor)

Total: 5 days from decision to go-live
```

---

## Risk Mitigation

```
Risk: Database incompatibility
├── Mitigation: Use same PostgreSQL version (18.x)
└── Verify: Table count, index count, data integrity

Risk: SSL certificate issues
├── Mitigation: Use Let's Encrypt with auto-renewal
└── Verify: Certificate valid, auto-renew working

Risk: Performance issues
├── Mitigation: Start with CPX31, monitor, upgrade if needed
└── Verify: All queries < 1s

Risk: Security breach
├── Mitigation: SSH key-only, firewall, fail2ban
└── Verify: No unauthorized access attempts

Risk: Data loss
├── Mitigation: Daily backups, verify restoration
└── Verify: Backup restorable before go-live
```
