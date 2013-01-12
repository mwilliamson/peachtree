angular.module('peachtree', [])

    .controller("RunningMachinesController", function($scope, $http) {
        $http({method: 'POST', url: '/running-machines'})
            .success(function(data, status, headers, config) {
                $scope.machines = data;
            })
            .error(function(data, status, headers, config) {
            });
        $scope.machines = []
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
    });
