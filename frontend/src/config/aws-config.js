// AWS Cognito Configuration
export const AWS_CONFIG = {
  // Cognito User Pool Configuration
  userPoolId: process.env.REACT_APP_USER_POOL_ID || 'us-east-1_zWg4kEMqF',
  userPoolClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || '23jnsoadeidihso1cr9de4gd5c',
  region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
  
  // API Gateway Configuration
  apiGatewayUrl: process.env.REACT_APP_API_URL || 'https://vph0fu827a.execute-api.us-east-1.amazonaws.com/prod',
  
  // Cognito Domain (for Hosted UI if needed)
  cognitoDomain: process.env.REACT_APP_COGNITO_DOMAIN || 'https://bedrock-diy-887078546492.auth.us-east-1.amazoncognito.com',
  
  // Application settings
  appName: 'AI 제목 생성기',
  
  // JWT Token settings
  tokenExpiration: 3600, // 1 hour in seconds
  refreshTokenExpiration: 86400 * 30, // 30 days in seconds
};

// Export individual values for convenience
export const {
  userPoolId,
  userPoolClientId,
  region,
  apiGatewayUrl,
  cognitoDomain,
  appName
} = AWS_CONFIG;