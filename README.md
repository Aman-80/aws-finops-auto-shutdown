
# AWS FinOps Auto-Shutdown System

Tag-based AWS resource scheduler that automatically stops non-production
environments after office hours, reducing dev/staging cloud costs by ~65%.

## Why this exists

Most companies leave dev/staging environments running 24/7 (168 hrs/week)
even though active development happens only ~45 hrs/week. The remaining
73% is pure waste. This system fixes that.

## Architecture

- **EventBridge** triggers Lambda on cron schedule (weekday shutdown 6PM, startup 9AM)
- **Lambda Scheduler** scans tagged resources, checks DynamoDB overrides, stops/starts
- **DynamoDB** holds developer override entries with TTL
- **Slack** receives daily cost summaries; `/keepup` command lets devs request overrides
- **Grafana** visualizes savings over time

## Tagging Strategy

| Tag Key         | Value Example       | Purpose                          |
|-----------------|---------------------|----------------------------------|
| `AutoShutdown`  | `true`              | Mark resource as managed         |
| `Environment`   | `dev` / `staging`   | Filter scope                     |
| `Schedule`      | `weekday-9-18`      | When it should be running        |

## Tech Stack

- **IaC:** Terraform
- **Compute:** AWS Lambda (Python 3.11)
- **Scheduler:** EventBridge cron rules
- **State:** DynamoDB
- **Notifications:** Slack webhooks + slash commands
- **Observability:** CloudWatch + Grafana

## Status

🚧 Under active development — see [milestones](docs/milestones.md)

## License

MIT
