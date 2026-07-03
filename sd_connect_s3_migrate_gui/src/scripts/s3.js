import { S3Client } from "@aws-sdk/client-s3";
import { getEC2Credentials, getS3endpoint } from "./openstack";

export async function createS3Client(scopedToken, projectId) {
  const s3address = getS3endpoint();
  const ec2 = await getEC2Credentials(scopedToken, projectId);
  return new S3Client({
    region: "us-east-1",
    endpoint: s3address,
    credentials: {
      accessKeyId: ec2.access,
      secretAccessKey: ec2.secret,
    },
  });
}
