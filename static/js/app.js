(function ($) {
    $(document).ready(function () {
        var socket = io();

        $('#sortOrder').change(function () {
            var sortOrder = $('#sortOrder').val();
            socket.emit('changeSortOrder', sortOrder);
        });

        // Event listener for form submission to add new sensor data
        $('#addSensorForm').submit(function (e) {
            e.preventDefault();

            var value = $('#value').val();
            $.ajax({
                url: '/add_data',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ 'value': parseFloat(value) }),
                success: function (response) {
                    console.log(response.message);
                    $("#message001").show().fadeOut(1000); 
                },
                error: function (error) {
                    console.error(error);
                }
            });
        });
        

        // Event listener for filter form submission
        $('#filterForm').submit(function (e) {
            e.preventDefault();
            applyFilter();
        });

        // Event listener for delete button clicks within the table
        $('#dataTable tbody').on('click', '.deleteBtn', function () {
            var id = $(this).data('id');
            deleteSensorData(id);
        });

        // Function to format a raw date string into a human-readable date and time
        function formatDateString(rawDate) {
            var options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
            var formattedDate = new Date(rawDate).toLocaleString('en-US', options);
            return formattedDate;
        }



        // Function to delete sensor data
        function deleteSensorData(id) {
            $.ajax({
                url: `/delete_data/${id}`,
                type: 'DELETE',
                success: function (response) {
                    console.log(response.message);
                    $("#message002").show().fadeOut(1000); 
                },
                error: function (error) {
                    console.error(error);
                }
            });
        }

        // Function to update the table with new data
        function updateTable(data) {
            var tableBody = $('#dataTable tbody');
            tableBody.empty();

            for (var i = 0; i < data.length; i++) {
                var rawDate = data[i].date;
                var date = formatDateString(rawDate);
                var value = data[i].value;
                var id = data[i].id;

                tableBody.append(`<tr id="row${id}"><td>${date}</td><td>${value}</td><td><button class="deleteBtn" data-id="${id}">Delete</button></td></tr>`);
            }
        }

        // Socket.IO event handler for receiving filtered data
        socket.on('updateFilteredData', function (data) {
            updateTable(data);
        });

        // Socket.IO event handler for receiving sensor data updates
        socket.on('updateSensorData', function (msg) {
            var tableBody = $('#dataTable tbody');
            tableBody.empty();

            for (var i = 0; i < msg.dates.length; i++) {
                var rawDate = msg.dates[i];
                var date = formatDateString(rawDate);
                var value = msg.values[i];
                var id = msg.ids[i];

                tableBody.append(`<tr id="row${id}"><td>${date}</td><td>${value}</td><td><button class="deleteBtn" data-id="${id}">Delete</button></td></tr>`);
            }
        });

        // ... additional event handlers or functions ...

    });
})(jQuery);

function formatDate(rawDate) {
    var formattedDate = new Date(rawDate).toLocaleDateString('en-US');
    return formattedDate;
}

function applyFilter() {
    var socket = io.connect();
    var startDate = $('#startDate').val();
    var endDate = $('#endDate').val();
    socket.emit('applyFilter', { start_date: startDate, end_date: endDate });
}

function resetFilter() {
    var socket = io.connect();
    $('#startDate').val('');
    $('#endDate').val('');
    
    // Send a reset signal to the server
    socket.emit('applyFilter', { start_date: '', end_date: '' });
}