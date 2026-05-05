pipeline {
    agent any
    
    environment {
        GNS3_SERVER_URL = 'http://192.168.56.102:80'
        PYTHONUNBUFFERED = '1' // Užtikrina, kad matytumėte log'us iškart
    }
    
    stages {
        stage('Checkout Code') {
            steps {
                deleteDir()
                git branch: 'main', url: 'https://github.com/DovydasIST23/Jenkins-LAN-Control.git'
            }
        }
        
        stage('Setup & Start GNS3') {
            steps {
                script {
                    // 1. Naudojame --no-cache, kad išvengtume strigimų dėl senų failų
                    // 2. Naudojame python -u (unbuffered), kad matytume kurioje vietoje stringa
                    bat """
                        pip install gns3fy netmiko --quiet --no-cache-dir
                        python -u str.py
                    """
                }
            }
        }
    }
    
    post {
        always {
            script {
                bat returnStatus: true, script: 'taskkill /F /IM python.exe /T'
            }
        }
    }
}
