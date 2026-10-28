// Parameterized Terraform pipeline for Terraform-learning (modules: ec2, iam, s3)
// Works on Windows and Linux Jenkins agents (uses bat or sh automatically).
// State is kept in Git (<module>/terraform.tfstate, see backend.tf). After every apply/destroy the
// pipeline commits and pushes it back to GitHub using the 'github-push-token' credential
// (Username with password: GitHub user + token with contents:write), so cleanWs() is safe.

def runCmd(String cmd) {
  if (isUnix()) { sh cmd } else { bat cmd }
}

pipeline {
  agent any

  parameters {
    choice(name: 'MODULE', choices: ['s3', 'iam', 'ec2'], description: 'Terraform root module to run')
    choice(name: 'ACTION', choices: ['plan', 'apply', 'destroy'], description: 'plan is read-only; apply/destroy require approval')
    string(name: 'BRANCH', defaultValue: 'main', description: 'Git branch to build')
  }

  environment {
    AWS_DEFAULT_REGION = 'us-east-1'   // matches the providers in ec2/iam/s3
    TF_IN_AUTOMATION   = 'true'
    TF_INPUT           = '0'
  }

  options {
    timestamps()
    disableConcurrentBuilds()   // avoid state-lock collisions
    timeout(time: 30, unit: 'MINUTES')
  }

  stages {
    stage('Checkout') {
      steps {
        git url: 'https://github.com/Malli-WAS/Terraform-learning.git', branch: params.BRANCH
        // Private repo? add: credentialsId: 'github-token'
      }
    }

    stage('Init & Validate') {
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-terraform-creds',
            accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']]) {
          dir(params.MODULE) {
            script {
              runCmd 'terraform fmt -check -recursive'
              runCmd 'terraform init -no-color'
              runCmd 'terraform validate -no-color'
            }
          }
        }
      }
    }

    stage('Plan') {
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-terraform-creds',
            accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']]) {
          dir(params.MODULE) {
            script {
              def destroyFlag = (params.ACTION == 'destroy') ? '-destroy' : ''
              runCmd "terraform plan -no-color ${destroyFlag} -out=tfplan"
              runCmd 'terraform show -no-color tfplan > plan.txt'
            }
          }
        }
        // Archived from workspace root so the path is <module>/plan.txt (what the MCP server reads)
        archiveArtifacts artifacts: "${params.MODULE}/plan.txt", fingerprint: true
      }
    }

    stage('Approval') {
      when { expression { params.ACTION in ['apply', 'destroy'] } }
      steps {
        input message: "Run terraform ${params.ACTION} on module '${params.MODULE}'? Review plan.txt first.",
              ok: 'Proceed'
      }
    }

    stage('Apply / Destroy') {
      when { expression { params.ACTION in ['apply', 'destroy'] } }
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-terraform-creds',
            accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']]) {
          dir(params.MODULE) {
            // Applies exactly the plan that was reviewed
            script {
              runCmd 'terraform apply -no-color tfplan'
            }
          }
        }
      }
      post {
        // Runs even if apply fails part-way: Terraform still writes partial state, which must be kept
        always {
          archiveArtifacts artifacts: "${params.MODULE}/terraform.tfstate", allowEmptyArchive: true
          // The Git plugin calls git.exe by full path, but bat steps need it on PATH (prepended; no-op on Linux)
          withEnv(['PATH+GIT=C:\\Program Files\\Git\\cmd']) {
          withCredentials([gitUsernamePassword(credentialsId: 'github-push-token')]) {
            script {
              runCmd "git add ${params.MODULE}/terraform.tfstate"
              runCmd "git diff --cached --quiet || git -c user.name=jenkins -c user.email=jenkins@localhost commit -m \"Update ${params.MODULE} state (${params.ACTION}, build #${env.BUILD_NUMBER})\""
              runCmd "git pull --rebase --autostash origin ${params.BRANCH}"
              runCmd "git push origin HEAD:${params.BRANCH}"
            }
          }
          }
        }
      }
    }
  }

  post {
    always { cleanWs() }
  }
}
