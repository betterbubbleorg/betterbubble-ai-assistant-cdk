"""
Monitoring Stack for AI Personal Assistant
Creates CloudWatch dashboards, alarms, and logging for monitoring.
"""

from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
    aws_logs as logs,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from typing import Optional


class CloudWatchStack(Stack):
    """CloudWatch monitoring and logging for AI Personal Assistant."""

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        config: dict,
        stacks: dict,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SNS topic for alerts
        self.alerts_topic = sns.Topic(
            self, "AlertsTopic",
            topic_name="betterbubble-ai-alerts",
            display_name="Better Bubble AI Assistant Alerts"
        )

        # Create CloudWatch Dashboard
        self.dashboard = cloudwatch.Dashboard(
            self, "AiAssistantDashboard",
            dashboard_name="BetterBubble-AI-Assistant"
        )

        # Add widgets to dashboard
        self.dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Lambda Invocations",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Invocations",
                        dimensions_map={
                            "FunctionName": "betterbubble-ai-task-manager"
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Invocations",
                        dimensions_map={
                            "FunctionName": "betterbubble-ai-assistant"
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Invocations",
                        dimensions_map={
                            "FunctionName": "betterbubble-ai-note-processor"
                        }
                    )
                ],
                width=12,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="Lambda Errors",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Errors",
                        dimensions_map={
                            "FunctionName": "betterbubble-ai-task-manager"
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Errors",
                        dimensions_map={
                            "FunctionName": "betterbubble-ai-assistant"
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Errors",
                        dimensions_map={
                            "FunctionName": "betterbubble-ai-note-processor"
                        }
                    )
                ],
                width=12,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="Lambda Duration",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Duration",
                        dimensions_map={
                            "FunctionName": "betterbubble-ai-task-manager"
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Duration",
                        dimensions_map={
                            "FunctionName": "betterbubble-ai-assistant"
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Duration",
                        dimensions_map={
                            "FunctionName": "betterbubble-ai-note-processor"
                        }
                    )
                ],
                width=12,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="DynamoDB Metrics",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="ConsumedReadCapacityUnits",
                        dimensions_map={
                            "TableName": "betterbubble-ai-users"
                        }
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="ConsumedWriteCapacityUnits",
                        dimensions_map={
                            "TableName": "betterbubble-ai-users"
                        }
                    )
                ],
                width=12,
                height=6
            )
        )

        # Create alarms for Lambda functions
        if stacks and 'lambda' in stacks:
            lambda_stack = stacks['lambda']
            # Lambda error alarm
            lambda_error_alarm = cloudwatch.Alarm(
                self, "LambdaErrorAlarm",
                alarm_name="BetterBubble-AI-Lambda-Errors",
                metric=cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    statistic="Sum",
                    period=Duration.minutes(5)
                ),
                threshold=5,
                evaluation_periods=2,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
            )

            # Lambda duration alarm
            lambda_duration_alarm = cloudwatch.Alarm(
                self, "LambdaDurationAlarm",
                alarm_name="BetterBubble-AI-Lambda-Duration",
                metric=cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    statistic="Average",
                    period=Duration.minutes(5)
                ),
                threshold=25000,  # 25 seconds in milliseconds
                evaluation_periods=2,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
            )

            # Add actions to alarms
            lambda_error_alarm.add_alarm_action(
                cloudwatch_actions.SnsAction(self.alerts_topic)
            )
            lambda_duration_alarm.add_alarm_action(
                cloudwatch_actions.SnsAction(self.alerts_topic)
            )

        # Create log group for application logs
        self.application_log_group = logs.LogGroup(
            self, "ApplicationLogGroup",
            log_group_name="/aws/lambda/betterbubble-ai-application",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create cost monitoring alarm
        cost_alarm = cloudwatch.Alarm(
            self, "CostAlarm",
            alarm_name="BetterBubble-AI-Cost-Alert",
            metric=cloudwatch.Metric(
                namespace="AWS/Billing",
                metric_name="EstimatedCharges",
                dimensions_map={
                    "Currency": "USD"
                },
                statistic="Maximum",
                period=Duration.days(1)
            ),
            threshold=50,  # Alert if costs exceed $50
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        cost_alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(self.alerts_topic)
        )
