// AWS Amplify v6 설정
export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_USER_POOL_ID || "us-east-1_PLACEHOLDER",
      userPoolClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || "placeholder",
      signUpVerificationMethod: "code",
      loginWith: {
        email: true,
      },
    },
  },
  API: {
    REST: {
      api: {
        endpoint:
          process.env.REACT_APP_API_URL ||
          "https://gcm3qzoy04.execute-api.us-east-1.amazonaws.com/prod",
        region: process.env.REACT_APP_AWS_REGION || "us-east-1",
      },
    },
  },
};

export default awsConfig;
