// AWS Amplify v6 설정
export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_USER_POOL_ID || "",
      userPoolClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || "",
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
          process.env.REACT_APP_API_URL || "",
        region: process.env.REACT_APP_AWS_REGION || "us-east-1",
      },
    },
  },
};

export default awsConfig;
