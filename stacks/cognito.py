"""
Authentication Stack for AI Personal Assistant
Creates Cognito user pool and client for user authentication.
"""

from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    custom_resources as cr,
    Duration,
    RemovalPolicy
)
from constructs import Construct


class CognitoStack(Stack):
    """Cognito user pool and authentication for AI Personal Assistant."""

    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Cognito User Pool
        self.user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name="betterbubble-ai-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=True
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                ),
                given_name=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                ),
                family_name=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                )
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=True,
                otp=True
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create User Pool Client
        self.user_pool_client = cognito.UserPoolClient(
            self, "UserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name="betterbubble-ai-client",
            generate_secret=False,  # For web/mobile apps
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=True
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE
                ],
                callback_urls=[
                    "http://localhost:3000/callback",
                    "https://betterbubble.org/callback"
                ],
                logout_urls=[
                    "http://localhost:3000/logout",
                    "https://betterbubble.org/logout"
                ]
            ),
            refresh_token_validity=Duration.days(30),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1)
        )

        # Create Identity Pool for AWS credentials
        self.identity_pool = cognito.CfnIdentityPool(
            self, "IdentityPool",
            identity_pool_name="betterbubble-ai-identity",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=self.user_pool_client.user_pool_client_id,
                    provider_name=self.user_pool.user_pool_provider_name
                )
            ]
        )

        # Create IAM role for authenticated users
        self.authenticated_role = iam.Role(
            self, "AuthenticatedRole",
            role_name="BetterBubble-AI-AuthenticatedRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity"
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Attach role to identity pool
        cognito.CfnIdentityPoolRoleAttachment(
            self, "IdentityPoolRoleAttachment",
            identity_pool_id=self.identity_pool.ref,
            roles={
                "authenticated": self.authenticated_role.role_arn
            }
        )

        # Create IAM users for admin access
        self.admin_user = iam.User(
            self, "AdminUser",
            user_name="betterbubble-admin",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
            ]
        )

        # Create IAM user for API access
        self.api_user = iam.User(
            self, "ApiUser",
            user_name="betterbubble-api",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add Bedrock permissions to API user
        self.api_user.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

        # Create access keys for API user (for programmatic access)
        self.api_access_key = iam.AccessKey(
            self, "ApiAccessKey",
            user=self.api_user
        )

        # Create limited access IAM user for Renee (chatbot only)
        self.renee_user = iam.User(
            self, "ReneeUser",
            user_name="renee",
            managed_policies=[]
        )

        # Create specific policy for Renee - chatbot access only
        self.renee_chatbot_policy = iam.Policy(
            self, "ReneeChatbotPolicy",
            policy_name="Renee-Chatbot-Access",
            statements=[
                # Allow access to the chatbot API
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "execute-api:Invoke"
                    ],
                    resources=[
                        f"arn:aws:execute-api:{self.region}:{self.account}:*/*/POST/ai"
                    ]
                ),
                # Allow basic Lambda execution for chatbot
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "lambda:InvokeFunction"
                    ],
                    resources=[
                        f"arn:aws:lambda:{self.region}:{self.account}:function:betterbubble-ai-assistant-*"
                    ]
                ),
                # Allow Bedrock access for AI responses
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    resources=["*"]
                ),
                # Allow CloudWatch logs for debugging
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/betterbubble-ai-assistant-*"
                    ]
                )
            ]
        )

        # Attach the limited policy to Renee's user
        self.renee_user.attach_inline_policy(self.renee_chatbot_policy)

        # Create access keys for Renee (for programmatic access)
        self.renee_access_key = iam.AccessKey(
            self, "ReneeAccessKey",
            user=self.renee_user
        )

        # Create IAM policy for authenticated users to access AI assistant
        self.ai_assistant_policy = iam.Policy(
            self, "AiAssistantPolicy",
            policy_name="BetterBubble-AI-Assistant-Policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    resources=["*"]
                ),
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
                    resources=[
                        f"arn:aws:dynamodb:{self.region}:{self.account}:table/betterbubble-ai-*"
                    ]
                )
            ]
        )

        # Attach AI assistant policy to authenticated role
        self.authenticated_role.attach_inline_policy(self.ai_assistant_policy)

        # Create Lambda function to create Cognito users
        self.user_creator_lambda = lambda_.Function(
            self, "UserCreatorLambda",
            function_name="betterbubble-user-creator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="user_creator.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import os

def handler(event, context):
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ['USER_POOL_ID']
        
        # Create the user "renee"
        try:
            response = cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username='renee',
                UserAttributes=[
                    {'Name': 'email', 'Value': 'renee@betterbubble.org'},
                    {'Name': 'given_name', 'Value': 'Renee'},
                    {'Name': 'family_name', 'Value': 'User'},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                TemporaryPassword='TempPass123!',
                MessageAction='SUPPRESS'  # Don't send welcome email
            )
            
            # Set permanent password
            cognito.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username='renee',
                Password='ReneePass123!',
                Permanent=True
            )
            
            print(f"Created user renee: {response['User']['Username']}")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'User renee created successfully'})
            }
            
        except cognito.exceptions.UsernameExistsException:
            print("User renee already exists")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'User renee already exists'})
            }
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
            """),
            timeout=Duration.seconds(30),
            log_group=logs.LogGroup(
                self, "UserCreatorLogGroup",
                log_group_name="/aws/lambda/betterbubble-user-creator",
                retention=logs.RetentionDays.ONE_WEEK
            ),
            environment={
                'USER_POOL_ID': self.user_pool.user_pool_id
            }
        )

        # Add Cognito permissions to the user creator Lambda
        self.user_creator_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminSetUserPassword",
                    "cognito-idp:AdminGetUser"
                ],
                resources=[self.user_pool.user_pool_arn]
            )
        )

        # Note: Custom attributes would need to be added via AWS Console or CLI
        # as CDK doesn't have direct support for adding custom attributes to existing UserPools
