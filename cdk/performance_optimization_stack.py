from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_apigateway as apigateway,
    CfnOutput,
    Duration
)
from constructs import Construct
from typing import Dict

class PerformanceOptimizationStack(Stack):
    """
    동적 프롬프트 시스템 성능 최적화 스택
    - Lambda 함수별 모니터링
    - 비용 최적화 알람
    - 모델 오케스트레이션 메트릭
    """
    
    def __init__(self, scope: Construct, construct_id: str, 
                 existing_lambdas: Dict[str, _lambda.Function] = None,
                 existing_api: apigateway.RestApi = None,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.lambdas = existing_lambdas or {}
        self.api = existing_api
        
        # 1. SNS 알람 토픽 생성
        self.create_alarm_topics()
        
        # 2. CloudWatch 대시보드 생성
        self.create_performance_dashboard()
        
        # 3. Lambda 알람 생성
        self.create_lambda_alarms()
        
        # 4. API Gateway 알람 생성
        if self.api:
            self.create_api_alarms()
        
        # 5. 출력값 생성
        self.create_outputs()
    
    def create_alarm_topics(self):
        """알람용 SNS 토픽 생성"""
        
        self.alarm_topic = sns.Topic(
            self, "AlarmTopic",
            display_name="동적 프롬프트 시스템 알람",
            topic_name="dynamic-prompt-system-alarms"
        )
        
        self.cost_alarm_topic = sns.Topic(
            self, "CostAlarmTopic", 
            display_name="비용 알람",
            topic_name="dynamic-prompt-cost-alarms"
        )
    
    def create_performance_dashboard(self):
        """성능 모니터링 대시보드 생성"""
        
        self.dashboard = cloudwatch.Dashboard(
            self, "PerformanceDashboard",
            dashboard_name="DynamicPromptSystem-Performance",
            default_interval=Duration.hours(1)
        )
        
        # Lambda 함수 메트릭 위젯들
        lambda_widgets = []
        
        for func_name, func in self.lambdas.items():
            # 실행 시간 위젯
            lambda_widgets.append(
                cloudwatch.GraphWidget(
                    title=f"{func_name} Lambda - 실행 시간",
                    left=[
                        func.metric_duration(statistic="Average"),
                        func.metric_duration(statistic="Maximum")
                    ],
                    width=6,
                    height=6
                )
            )
            
            # 오류율 위젯
            lambda_widgets.append(
                cloudwatch.GraphWidget(
                    title=f"{func_name} Lambda - 오류/성공률",
                    left=[func.metric_errors()],
                    right=[func.metric_invocations()],
                    width=6,
                    height=6
                )
            )
        
        # 위젯을 대시보드에 추가
        if lambda_widgets:
            self.dashboard.add_widgets(*lambda_widgets)
    
    def create_lambda_alarms(self):
        """Lambda 함수별 알람 생성"""
        
        for func_name, func in self.lambdas.items():
            # 오류율 알람
            cloudwatch.Alarm(
                self, f"{func_name}ErrorAlarm",
                metric=func.metric_errors(period=Duration.minutes(5)),
                threshold=5,
                evaluation_periods=2,
                alarm_description=f"{func_name} Lambda 함수 오류율이 높습니다",
                actions_enabled=True
            ).add_alarm_action(
                cw_actions.SnsAction(self.alarm_topic)
            )
            
            # 실행 시간 알람 (generate Lambda만)
            if func_name == "generate":
                cloudwatch.Alarm(
                    self, f"{func_name}DurationAlarm",
                    metric=func.metric_duration(period=Duration.minutes(5)),
                    threshold=30000,  # 30초
                    evaluation_periods=3,
                    alarm_description=f"{func_name} Lambda 실행 시간이 초과했습니다",
                    actions_enabled=True
                ).add_alarm_action(
                    cw_actions.SnsAction(self.alarm_topic)
                )
    
    def create_api_alarms(self):
        """API Gateway 알람 생성"""
        
        # 4XX 오류 알람
        cloudwatch.Alarm(
            self, "Api4XXErrorAlarm",
            metric=self.api.metric_client_error(period=Duration.minutes(5)),
            threshold=10,
            evaluation_periods=2,
            alarm_description="API Gateway 4XX 오류율이 높습니다"
        ).add_alarm_action(
            cw_actions.SnsAction(self.alarm_topic)
        )
        
        # 5XX 오류 알람
        cloudwatch.Alarm(
            self, "Api5XXErrorAlarm",
            metric=self.api.metric_server_error(period=Duration.minutes(5)),
            threshold=5,
            evaluation_periods=2,
            alarm_description="API Gateway 5XX 오류율이 높습니다"
        ).add_alarm_action(
            cw_actions.SnsAction(self.alarm_topic)
        )
    
    def create_outputs(self):
        """출력값 생성"""
        
        CfnOutput(
            self, "AlarmTopicArn",
            value=self.alarm_topic.topic_arn,
            description="일반 알람 SNS 토픽 ARN",
            export_name="DynamicPromptAlarmTopicArn"
        )
        
        CfnOutput(
            self, "CostAlarmTopicArn",
            value=self.cost_alarm_topic.topic_arn,
            description="비용 알람 SNS 토픽 ARN",
            export_name="DynamicPromptCostAlarmTopicArn"
        )
        
        CfnOutput(
            self, "DashboardUrl",
            value=f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.dashboard.dashboard_name}",
            description="CloudWatch 대시보드 URL",
            export_name="DynamicPromptDashboardUrl"
        ) 