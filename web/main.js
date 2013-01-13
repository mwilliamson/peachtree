angular.module('peachtree', [])
    
    .controller("DashboardController", function($scope) {
        $scope.formatTime = function(time) {
            if (time) {
                var date = new Date(time * 1000);
                return date.toISOString();
            } else {
                return null;
            }
        };
        
        $scope.view = function(machine) {
            $scope.selectedMachine = machine;
        };
    })
    
    .controller("RunningMachinesController", function($scope, $http) {
        $http({method: 'POST', url: '/running-machines'})
            .success(function(data, status, headers, config) {
                $scope.machines = data;
            })
            .error(function(data, status, headers, config) {
            });
            
        $scope.stop = function(machine) {
            var arguments = {"identifier": machine.identifier};
            $http({method: "POST", url: "/destroy", data: arguments});
        };
    })
    
    .controller("AvailableImagesController", function($scope, $http) {
        $http({method: 'POST', url: '/available-images'})
            .success(function(data, status, headers, config) {
                var images = data;
                images.sort();
                $scope.images = images;
            })
            .error(function(data, status, headers, config) {
            });
        
        $scope.start = function(imageName) {
            var arguments = {"image-name": imageName, "public-ports": "22"};
            $http({method: "POST", url: "/start", data: arguments});
        };
    })
    
    .controller("MachineController", function($scope) {
    });
