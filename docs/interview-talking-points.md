# Interview Talking Points — FinOps Auto-Shutdown

## 30-Second Elevator Pitch

> "I built a serverless system that auto-shuts down dev/staging AWS resources
> after office hours. It uses tag-based discovery, has a Slack-integrated override
> mechanism for developers working late, and tracks savings via CloudWatch dashboards.
> In a 50-instance dev fleet, this approach saves ~₹1.7 lakh annually.
> Built with Terraform, Lambda, DynamoDB, and EventBridge."

## Likely Questions & Answers

### Q: Why didn't you just write a cron script on a server?
**A:** Three reasons:
1. **Reliability** — a server can die. Lambda + EventBridge has 99.99% SLA.
2. **Cost** — running a server 24×7 to save money is ironic. Lambda is ₹0 idle.
3. **Scalability** — Lambda scales horizontally for free; a script doesn't.

### Q: How do you prevent accidentally stopping production?
**A:** Three layers of safety:
1. **Tag-based filter** — only `AutoShutdown=true` resources are touched
2. **Environment tag check** — separate scope from prod
3. **Default deny** — un-tagged resources are never affected

### Q: What if the override check fails (DynamoDB outage)?
**A:** Fail-open. The scheduler proceeds with the action.
Reasoning: cost-saving reliability matters more than override convenience.
A DynamoDB outage shouldn't prevent scheduled shutdowns.

### Q: Idempotency — what if Lambda is invoked twice for the same schedule?
**A:** AWS `stop_instances` / `start_instances` are idempotent.
Calling stop on an already-stopped instance is a no-op.
This lets the scheduler safely retry on EventBridge re-deliveries.

### Q: How do you handle secrets?
**A:** SSM Parameter Store with SecureString type (KMS-encrypted).
Lambda fetches the webhook URL at cold start and caches it for warm invocations.
Never hardcoded, never committed — `terraform.tfvars` is gitignored.

### Q: How would you scale this to multiple regions?
**A:** Two options:
1. **One Lambda per region** — duplicate Terraform per region, simpler but more overhead
2. **Single Lambda, cross-region calls** — STS + region loop, more code complexity

I'd choose Option 1 for production — failure isolation, simpler ops.

### Q: How would you handle a DST (daylight saving time) transition?
**A:** EventBridge cron uses UTC.
The schedule is fixed in UTC, so a 6 PM IST shutdown happens at 12:30 PM UTC year-round.
For regions that observe DST, I'd use timezone-aware scheduling via Step Functions.

### Q: What's your monitoring story?
**A:** Three signals:
1. **Lambda errors** — CloudWatch alarms on error rate
2. **Custom business metrics** — instances affected, savings tracked
3. **Slack visibility** — every action posts a summary

If a scheduled run produces 0 actions for 3 days straight, an alarm would fire
(silent failure detection).

### Q: What would you build next?
**A:**
1. **Slack slash command** — replace CLI override with native UX
2. **Cost attribution per team** — tag-based, route to FinOps Slack channel
3. **Anomaly detection** — flag if savings drop unexpectedly (means tags missing)
4. **EKS, RDS, ASG support** — expand resource types

## What This Project Demonstrates

- **Business thinking** — not just code, but cost impact reasoning
- **Engineering empathy** — override mechanism = developer experience consideration
- **Production patterns** — fail-open, idempotency, observability, IaC
- **Trade-off literacy** — explained DynamoDB vs RDS, SSM vs Secrets Manager, Lambda vs Fargate
- **End-to-end ownership** — infra → code → notifications → dashboards
