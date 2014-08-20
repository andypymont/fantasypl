function getTeamFormation() {
		var g = 0;
		var d = 0;
		var m = 0;
		var f = 0;

	$('.starterrow.in').each(function() {
		$(this).find('.btn').each(function() {
			if ($(this).hasClass("posicon-G")) { g++; }
			if ($(this).hasClass("posicon-D")) { d++; }
			if ($(this).hasClass("posicon-M")) { m++; }
			if ($(this).hasClass("posicon-F")) { f++; }
		});
	});

	var positions = [g.toString(), d.toString(), m.toString(), f.toString()];
	return positions.join("-");
}

function validFormation(formation) {
	var validFormations = ['1-5-3-2', '1-5-4-1', '1-4-5-1', '1-4-4-2', '1-4-3-3', '1-3-5-2', '1-3-4-3']
	return (validFormations.indexOf(formation) > -1);
}

function updateFormationValidity() {
	/* update current formation text and good/bad indicator */
	var formation = getTeamFormation();
	$('.formation').text("Current Formation: ".concat(formation));
	if (validFormation(formation)) {
		$('#formationvalid').removeClass("out").addClass("in");
		$('#formationinvalid').removeClass("in").addClass("out");
		$('#btn-savelineup').removeClass("disabled");
	} else {
		$('#formationvalid').removeClass("in").addClass("out");
		$('#formationinvalid').removeClass("out").addClass("in");
		$('#btn-savelineup').addClass("disabled");
	}
}

function checkboxToggle() {
		/* capture status we are switching to */
		var inlineup = $(this).is(':checked');

		/* calculate ID number */
		var playerno = $(this).attr('id').replace('startercheck', '').replace('subcheck', '');

		/* set both checkboxes to the right value */
		$('#'.concat('startercheck').concat(playerno)).prop('checked', inlineup);
		$('#'.concat('subcheck').concat(playerno)).prop('checked', inlineup);

		/* collapse in/out the right table rows */
		if (inlineup) {
			$('#'.concat('starterrow').concat(playerno)).removeClass("out").addClass("in");
			$('#'.concat('subrow').concat(playerno)).removeClass("in").addClass("out");
		} else {
			$('#'.concat('starterrow').concat(playerno)).removeClass("in").addClass("out");
			$('#'.concat('subrow').concat(playerno)).removeClass("out").addClass("in");
		}
		/* reflect whether formation is valid in the interface */
		updateFormationValidity();
};

function pad(v, size) {
	var s = "" + v;
	while (s.length < size) {
		s = "0" + s;
	}
	return s;
}

function prettyDate(dt) {
	var weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
	return weekdays[dt.getDay()] + " " + pad(dt.getDate(), 2) + "/" + pad(dt.getMonth(), 2) + "/" + pad(dt.getFullYear(), 4) + " " 
		   + pad(dt.getHours(), 2) + ":" + pad(dt.getMinutes(), 2);
}

function addPlayerModal(playername, playerid, waiver) {
	$('#addPlayerName').text(playername);
	$('#addPlayer').val(playerid);

	if ( waiver ) {
		$('#addPlayerWaiverNotice').removeClass("out").addClass("in");
	}
	else {
		$('#addPlayerWaiverNotice').removeClass("in").addClass("out");
	}
	$('#addPlayerModal').modal('show');
}

function moveUp(row_no) {
	var row = $("tr#waiverclaimx".replace('x', row_no));
	var previous = row.prev();

	// check to see if it is a row
	if (previous.is("tr") && !(previous.hasClass("waiverclaimheadings"))) {

		// move row above previous
		row.detach();
		previous.before(row);

		// draw attention
		row.fadeIn();
	}
	// else - already at the top

	// update current ordering:
	$("#priorities").val(currentOrder());
}

function moveDown(row_no) {
	var row = $("tr#waiverclaimx".replace('x', row_no));
	var nxt = row.next();

	// check to see if it is a row
	if (nxt.is("tr")) {

		// move row beyond next
		row.detach();
		nxt.after(row);

		// draw attention
		row.fadeIn();
	}
	// else - already at the bottom

	// update current ordering:
	$("#priorities").val(currentOrder());
}

function currentOrder() {
	var ids = [];
	$("#waiverclaims tr td.claimno").each( function() {
		ids.push($(this).text());
	});	
	return ids;
}

$(document).ready(function() {

	$('.startercheck').change(checkboxToggle);
	$('.subcheck').change(checkboxToggle);

	$('.player-dropdown').select2({
		placeholder: "Select a player",
		ajax: {
			url: JSON_TEAM_PLAYERS,
			data: function(term, page) {
				return { q: term };
			},
			results: function(data, page) {
				return {results: data.players};
			}
		}
	});

	$('.deadline').text(prettyDate(new Date(TIME_DEADLINE)));
	updateFormationValidity();
});