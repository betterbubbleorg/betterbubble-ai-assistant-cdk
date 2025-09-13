"""
Database Stack for AI Personal Assistant
Creates DynamoDB tables for user data, tasks, appointments, notes, and conversations.
"""

from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    aws_kms as kms,
    RemovalPolicy,
    Duration
)
from constructs import Construct
from typing import Optional


class DynamoDBStack(Stack):
    """DynamoDB tables for AI Personal Assistant data storage."""

    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create KMS key for encryption
        self.encryption_key = kms.Key(
            self, "DatabaseEncryptionKey",
            description="KMS key for DynamoDB encryption",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Users table - stores user profiles and preferences
        self.users_table = dynamodb.Table(
            self, "UsersTable",
            table_name=config.generate_stack_name("users"),
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # Tasks table - stores user tasks and todos
        self.tasks_table = dynamodb.Table(
            self, "TasksTable",
            table_name=config.generate_stack_name("tasks"),
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="task_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # Appointments table - stores scheduled appointments
        self.appointments_table = dynamodb.Table(
            self, "AppointmentsTable",
            table_name=config.generate_stack_name("appointments"),
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="appointment_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # Notes table - stores user notes and ideas
        self.notes_table = dynamodb.Table(
            self, "NotesTable",
            table_name=config.generate_stack_name("notes"),
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="note_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # AI Conversations table - stores chat history
        self.conversations_table = dynamodb.Table(
            self, "ConversationsTable",
            table_name=config.generate_stack_name("conversations"),
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="conversation_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # Reminders table - stores persistent reminders and memories
        self.reminders_table = dynamodb.Table(
            self, "RemindersTable",
            table_name=config.generate_stack_name("reminders"),
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="reminder_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # Add GSI for tasks by status
        self.tasks_table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="due_date",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Add GSI for appointments by date
        self.appointments_table.add_global_secondary_index(
            index_name="date-index",
            partition_key=dynamodb.Attribute(
                name="appointment_date",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="appointment_time",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Add GSI for notes by category
        self.notes_table.add_global_secondary_index(
            index_name="category-index",
            partition_key=dynamodb.Attribute(
                name="category",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Add GSI for reminders by due date
        self.reminders_table.add_global_secondary_index(
            index_name="due-date-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="due_date",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Add GSI for conversations by topic
        self.conversations_table.add_global_secondary_index(
            index_name="topic-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="topic",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Search History table - tracks web search results to avoid repetition
        self.search_history_table = dynamodb.Table(
            self, "SearchHistoryTable",
            table_name=config.generate_stack_name("search-history"),
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="search_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # Add GSI for search history by topic
        self.search_history_table.add_global_secondary_index(
            index_name="topic-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="topic",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Admin Knowledge table - stores permanent admin-defined knowledge
        self.admin_knowledge_table = dynamodb.Table(
            self, "AdminKnowledgeTable",
            table_name=config.generate_stack_name("admin-knowledge"),
            partition_key=dynamodb.Attribute(
                name="knowledge_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # Budget table - stores spending and budget tracking for BetterBubble
        self.budget_table = dynamodb.Table(
            self, "BudgetTable",
            table_name=config.generate_stack_name("budget"),
            partition_key=dynamodb.Attribute(
                name="budget_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # Add GSI for budget by organization
        self.budget_table.add_global_secondary_index(
            index_name="organization-index",
            partition_key=dynamodb.Attribute(
                name="organization",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Add GSI for budget by category
        self.budget_table.add_global_secondary_index(
            index_name="category-index",
            partition_key=dynamodb.Attribute(
                name="category",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            )
        )
