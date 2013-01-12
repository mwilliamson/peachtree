angular.module('peachtree', [])
    .controller("RunningMachinesController", function($scope) {
        $scope.machines = [
            {
                "identifier": "not-a-real-machine"
            }
        ]
    });
