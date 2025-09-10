"""
Backend Stack for AI Personal Assistant
Creates Lambda functions and API Gateway for the backend services.
"""

from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_logs as logs,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from typing import Optional


class LambdaStack(Stack):
    """Lambda functions and API Gateway for AI Personal Assistant."""

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        config: dict,
        stacks: dict,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM role for Lambda functions
        self.lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            role_name="BetterBubble-AI-LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add DynamoDB permissions
        if stacks and 'dynamodb' in stacks:
            dynamodb_stack = stacks['dynamodb']
            # Get actual table ARNs from the DynamoDB stack
            table_arns = []
            if hasattr(dynamodb_stack, 'users_table'):
                table_arns.append(dynamodb_stack.users_table.table_arn)
            if hasattr(dynamodb_stack, 'tasks_table'):
                table_arns.append(dynamodb_stack.tasks_table.table_arn)
            if hasattr(dynamodb_stack, 'appointments_table'):
                table_arns.append(dynamodb_stack.appointments_table.table_arn)
            if hasattr(dynamodb_stack, 'notes_table'):
                table_arns.append(dynamodb_stack.notes_table.table_arn)
            if hasattr(dynamodb_stack, 'conversations_table'):
                table_arns.append(dynamodb_stack.conversations_table.table_arn)
            
            if table_arns:
                self.lambda_role.add_to_policy(
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:DeleteItem",
                            "dynamodb:Query",
                            "dynamodb:Scan"
                        ],
                        resources=table_arns
                    )
                )

        # Add Bedrock permissions
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

        # Add KMS permissions for DynamoDB encryption
        if stacks and 'dynamodb' in stacks:
            dynamodb_stack = stacks['dynamodb']
            if hasattr(dynamodb_stack, 'encryption_key'):
                self.lambda_role.add_to_policy(
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "kms:Decrypt",
                            "kms:GenerateDataKey"
                        ],
                        resources=[dynamodb_stack.encryption_key.key_arn]
                    )
                )

        # Task Manager Lambda Function
        self.task_manager_lambda = lambda_.Function(
            self, "TaskManagerLambda",
            function_name=config.generate_stack_name("task-manager"),
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.handler",
            code=lambda_.Code.from_asset("lambda_functions/task_manager"),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            log_group=logs.LogGroup(
                self, "TaskManagerLogGroup",
                log_group_name=f"/aws/lambda/{config.generate_stack_name('task-manager')}",
                retention=logs.RetentionDays.ONE_WEEK
            ),
            environment={
                'TASKS_TABLE_NAME': stacks['dynamodb'].tasks_table.table_name if stacks and 'dynamodb' in stacks else ''
            }
        )

        # Create Lambda layer for dependencies
        self.dependencies_layer = lambda_.LayerVersion(
            self, "DependenciesLayer",
            layer_version_name=config.generate_stack_name("dependencies-layer"),
            code=lambda_.Code.from_asset("lambda_layers"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_13],
            description="Dependencies for AI Assistant Lambda functions"
        )

        # AI Assistant Lambda Function
        self.ai_assistant_lambda = lambda_.Function(
            self, "AiAssistantLambda",
            function_name=config.generate_stack_name("ai-assistant"),
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.handler",
            code=lambda_.Code.from_asset("lambda_functions/ai_assistant"),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            layers=[self.dependencies_layer],
            log_group=logs.LogGroup(
                self, "AiAssistantLogGroup",
                log_group_name=f"/aws/lambda/{config.generate_stack_name('ai-assistant')}",
                retention=logs.RetentionDays.ONE_WEEK
            ),
            environment={
                'CONVERSATIONS_TABLE_NAME': stacks['dynamodb'].conversations_table.table_name if stacks and 'dynamodb' in stacks else '',
                'COGNITO_USER_POOL_ID': stacks['cognito'].user_pool.user_pool_id if stacks and 'cognito' in stacks else '',
                'COGNITO_USER_POOL_CLIENT_ID': stacks['cognito'].user_pool_client.user_pool_client_id if stacks and 'cognito' in stacks else ''
            }
        )

        # Note Processor Lambda Function
        self.note_processor_lambda = lambda_.Function(
            self, "NoteProcessorLambda",
            function_name=config.generate_stack_name("note-processor"),
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.handler",
            code=lambda_.Code.from_asset("lambda_functions/note_processor"),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            log_group=logs.LogGroup(
                self, "NoteProcessorLogGroup",
                log_group_name=f"/aws/lambda/{config.generate_stack_name('note-processor')}",
                retention=logs.RetentionDays.ONE_WEEK
            ),
            environment={
                'NOTES_TABLE_NAME': stacks['dynamodb'].notes_table.table_name if stacks and 'dynamodb' in stacks else ''
            }
        )

        # Create API Gateway
        self.api = apigateway.RestApi(
            self, "AiAssistantApi",
            rest_api_name="BetterBubble AI Assistant API",
            description="API Gateway for AI Personal Assistant",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            ),
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            )
        )

        # Add API Gateway permissions to Lambda role
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            )
        )

        # Create API endpoints
        tasks_resource = self.api.root.add_resource("tasks")
        tasks_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.task_manager_lambda)
        )
        tasks_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.task_manager_lambda)
        )

        notes_resource = self.api.root.add_resource("notes")
        notes_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.note_processor_lambda)
        )
        notes_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.note_processor_lambda)
        )

        ai_resource = self.api.root.add_resource("ai")
        ai_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.ai_assistant_lambda)
        )

        # Health check endpoint
        health_resource = self.api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.task_manager_lambda)
        )
