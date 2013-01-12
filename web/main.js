angular.module('peachtree', [])

    .controller("RunningMachinesController", function($scope, $http) {
        $http({method: 'POST', url: '/running-machines'})
            .success(function(data, status, headers, config) {
                $scope.machines = data;
            })
            .error(function(data, status, headers, config) {
            });
        $scope.machines = []
    });
