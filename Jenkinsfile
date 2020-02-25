pipeline {
  agent none
  stages {
    stage('test_on_centos7') {
      agent {
        node {
          label 'centos7'
        }

      }
      steps {
        echo 'hello'
        sh 'echo this is cent os 7'
      }
    }

    stage('test_on_windows') {
      agent {
        node {
          label 'master'
        }

      }
      steps {
        bat 'echo hello world'
      }
    }

  }
}