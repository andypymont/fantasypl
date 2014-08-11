function getTeamFormation() {
		var g = 0;
		var d = 0;
		var m = 0;
		var f = 0;

	$('.starterrow.in').each(function() {
		$(this).find('.btn').each(function() {
			if ($(this).hasClass("posicon-g")) { g++; }
			if ($(this).hasClass("posicon-d")) { d++; }
			if ($(this).hasClass("posicon-m")) { m++; }
			if ($(this).hasClass("posicon-f")) { f++; }
		});
	});

	var positions = [g.toString(), d.toString(), m.toString(), f.toString()];
	return positions.join("-");
}

function validFormation(formation) {
	var validFormations = ['1-5-3-2', '1-5-4-1', '1-4-5-1', '1-4-4-2', '1-4-3-3', '1-3-5-2', '1-3-4-3']
	return (validFormations.indexOf(formation) > -1);
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

};

$(document).ready(function() {

	$('.startercheck').change(checkboxToggle);
	$('.subcheck').change(checkboxToggle);

});