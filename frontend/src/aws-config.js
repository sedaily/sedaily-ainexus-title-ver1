// AWS Amplify v6 설정
export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_USER_POOL_ID || "us-east-1_i8lrt1eIK",
      userPoolClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || "65034130jm8bj9kvrqokj3g479",
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
          "https://bu1n1ihwo4.execute-api.us-east-1.amazonaws.com/prod",
        region: process.env.REACT_APP_AWS_REGION || "us-east-1",
      },
    },
  },
};

export default awsConfig;
