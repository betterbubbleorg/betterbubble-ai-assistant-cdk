"""
AI Services Stack for AI Personal Assistant
Creates Bedrock foundation models, Knowledge Base, Agent, and web crawling.
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_iam as iam,
    aws_bedrock as bedrock,
    aws_kms as kms,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_events as events,
    aws_events_targets as targets,
    aws_cloudformation as cfn,
    aws_ssm as ssm
)
from constructs import Construct
from typing import Optional


class BedrockStack(Stack):
    """Amazon Bedrock and AI services for personal assistant."""

    def __init__(self, scope: Construct, construct_id: str, config: dict, stacks: dict = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create KMS key for Bedrock encryption
        self.bedrock_key = kms.Key(
            self, "BedrockEncryptionKey",
            description="KMS key for Bedrock model encryption",
            enable_key_rotation=True
        )

        # Create IAM role for Bedrock access
        self.bedrock_role = iam.Role(
            self, "BedrockExecutionRole",
            role_name="BetterBubble-AI-BedrockRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add Bedrock permissions
        self.bedrock_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:GetFoundationModel",
                    "bedrock:ListFoundationModels"
                ],
                resources=["*"]
            )
        )

        # Add KMS permissions for encryption
        self.bedrock_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kms:Decrypt",
                    "kms:GenerateDataKey"
                ],
                resources=[self.bedrock_key.key_arn]
            )
        )

        # Create Knowledge Base
        self.knowledge_base = BedrockKnowledgeBase(
            self, "KnowledgeBase",
            bucket_name=f"betterbubble-kb-{self.account}-{self.region}",
            knowledge_base_role=self.bedrock_role,
            stack_name=self.stack_name
        )

        # Create Bedrock Agent
        self.bedrock_agent = BedrockAgent(
            self, "BedrockAgent",
            knowledge_base_id=self.knowledge_base.knowledge_base_id,
            agent_role=self.bedrock_role,
            stack_name=self.stack_name
        )

        # Create SSM parameters for search engine API keys
        self.search_parameters = self.create_search_parameters()

        # Create Web Crawler
        dependencies_layer = stacks['lambda'].dependencies_layer if stacks and 'lambda' in stacks else None
        self.web_crawler = WebCrawler(
            self, "WebCrawler",
            bucket=self.knowledge_base.bucket,
            dependencies_layer=dependencies_layer,
            stack_name=self.stack_name,
            search_parameters=self.search_parameters
        )

    def create_search_parameters(self):
        """Create SSM parameters for search engine API keys."""
        
        # Google Custom Search parameters
        google_api_key_param = ssm.StringParameter(
            self, "GoogleApiKeyParameter",
            parameter_name=f"/{self.stack_name}/search/google-api-key",
            description="Google Custom Search API Key - Set this to your actual API key",
            string_value="NOT_SET",  # Placeholder value, user needs to set this
            tier=ssm.ParameterTier.STANDARD  # Free tier
        )
        
        google_search_engine_id_param = ssm.StringParameter(
            self, "GoogleSearchEngineIdParameter",
            parameter_name=f"/{self.stack_name}/search/google-search-engine-id",
            description="Google Custom Search Engine ID - Set this to your actual search engine ID",
            string_value="NOT_SET",  # Placeholder value, user needs to set this
            tier=ssm.ParameterTier.STANDARD  # Free tier
        )
        
        # Bing Search API parameter
        bing_api_key_param = ssm.StringParameter(
            self, "BingApiKeyParameter",
            parameter_name=f"/{self.stack_name}/search/bing-api-key",
            description="Bing Search API Key - Set this to your actual API key",
            string_value="NOT_SET",  # Placeholder value, user needs to set this
            tier=ssm.ParameterTier.STANDARD  # Free tier
        )
        
        return {
            'google_api_key': google_api_key_param,
            'google_search_engine_id': google_search_engine_id_param,
            'bing_api_key': bing_api_key_param
        }


class BedrockKnowledgeBase(Construct):
    """Bedrock Knowledge Base with S3 data source."""

    def __init__(self, scope: Construct, construct_id: str, bucket_name: str, knowledge_base_role: iam.Role, stack_name: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 bucket for Knowledge Base data source
        self.bucket = s3.Bucket(
            self, "KnowledgeBaseBucket",
            bucket_name=bucket_name,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteIncompleteMultipartUploads",
                    abort_incomplete_multipart_upload_after=Duration.days(1)
                ),
                s3.LifecycleRule(
                    id="TransitionToIA",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        )
                    ]
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True  # Automatically delete objects when stack is deleted
        )

        # Add Knowledge Base permissions to role
        knowledge_base_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:CreateKnowledgeBase",
                    "bedrock:GetKnowledgeBase",
                    "bedrock:UpdateKnowledgeBase",
                    "bedrock:DeleteKnowledgeBase",
                    "bedrock:ListKnowledgeBases",
                    "bedrock:CreateDataSource",
                    "bedrock:GetDataSource",
                    "bedrock:UpdateDataSource",
                    "bedrock:DeleteDataSource",
                    "bedrock:ListDataSources",
                    "bedrock:StartIngestionJob",
                    "bedrock:GetIngestionJob",
                    "bedrock:ListIngestionJobs",
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate"
                ],
                resources=["*"]
            )
        )

        # Add S3 permissions
        knowledge_base_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:GetObjectVersion"
                ],
                resources=[
                    self.bucket.bucket_arn,
                    f"{self.bucket.bucket_arn}/*"
                ]
            )
        )

        # Store bucket name for reference
        self.bucket_name = self.bucket.bucket_name
        self.knowledge_base_id = f"{stack_name}-knowledge-base"


class BedrockAgent(Construct):
    """Bedrock Agent with Knowledge Base integration."""

    def __init__(self, scope: Construct, construct_id: str, knowledge_base_id: str, agent_role: iam.Role, stack_name: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Add agent permissions to role
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:CreateAgent",
                    "bedrock:GetAgent",
                    "bedrock:UpdateAgent",
                    "bedrock:DeleteAgent",
                    "bedrock:ListAgents",
                    "bedrock:CreateAgentActionGroup",
                    "bedrock:GetAgentActionGroup",
                    "bedrock:UpdateAgentActionGroup",
                    "bedrock:DeleteAgentActionGroup",
                    "bedrock:ListAgentActionGroups",
                    "bedrock:CreateAgentAlias",
                    "bedrock:GetAgentAlias",
                    "bedrock:UpdateAgentAlias",
                    "bedrock:DeleteAgentAlias",
                    "bedrock:ListAgentAliases",
                    "bedrock:InvokeAgent",
                    "bedrock:PrepareAgent"
                ],
                resources=["*"]
            )
        )

        # Add Knowledge Base permissions for agent
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate"
                ],
                resources=["*"]
            )
        )

        # Create CloudWatch Log Group for agent
        self.agent_log_group = logs.LogGroup(
            self, "BedrockAgentLogGroup",
            log_group_name=f"/aws/bedrock/agents/{stack_name}-agent",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Store agent ID for reference
        self.agent_id = f"{stack_name}-agent"


class WebCrawler(Construct):
    """Web crawler Lambda function for internet data collection."""

    def __init__(self, scope: Construct, construct_id: str, bucket: s3.Bucket, dependencies_layer: lambda_.LayerVersion = None, stack_name: str = None, search_parameters: dict = None, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda function for web crawling
        function_name = f"{stack_name}-document-processor" if stack_name else "betterbubble-document-processor"
        self.crawler_function = lambda_.Function(
            self, "CrawlerFunction",
            function_name=function_name,
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.handler",
            code=lambda_.Code.from_asset("lambda_functions/web_crawler"),
            layers=[dependencies_layer] if dependencies_layer else [],
            environment={
                'BUCKET_NAME': bucket.bucket_name,
                'SEARCH_QUERIES': 'AI news,technology updates,programming tutorials,latest tech trends',
                'SEARCH_ENGINE': 'duckduckgo',  # duckduckgo, google, bing
                'GOOGLE_API_KEY_PARAM': search_parameters['google_api_key'].parameter_name if search_parameters else '',
                'GOOGLE_SEARCH_ENGINE_ID_PARAM': search_parameters['google_search_engine_id'].parameter_name if search_parameters else '',
                'BING_API_KEY_PARAM': search_parameters['bing_api_key'].parameter_name if search_parameters else ''
            },
            timeout=Duration.minutes(5),
            memory_size=256  # Free tier: 1M requests, 400,000 GB-seconds
        )

        # Grant S3 permissions to Lambda
        bucket.grant_read_write(self.crawler_function)
        
        # Grant SSM parameter read permissions to Lambda
        if search_parameters:
            for param in search_parameters.values():
                param.grant_read(self.crawler_function)

        # Create EventBridge rule for scheduled crawling
        rule_name = f"{stack_name}-crawling-schedule" if stack_name else "betterbubble-crawling-schedule"
        self.crawling_schedule = events.Rule(
            self, "CrawlingSchedule",
            rule_name=rule_name,
            schedule=events.Schedule.rate(Duration.hours(6)),  # Run every 6 hours
            description="Schedule for web crawling"
        )

        # Add Lambda as target
        self.crawling_schedule.add_target(
            targets.LambdaFunction(self.crawler_function)
        )
